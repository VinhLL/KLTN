import json
import os
import re
from neo4j import GraphDatabase, exceptions
from dotenv import load_dotenv

load_dotenv()

def sanitize_identifier(s: str) -> str:
    """Loại bỏ backticks và ký tự không an toàn, giữ lại letters, digits, underscore và space.
       Trả về chuỗi đã strip. (sử dụng để tạo label/rel/property key an toàn).
    """
    if s is None:
        return ""
    s = str(s)
    # loại backticks
    s = s.replace("`", "")
    # chuẩn hóa unicode spacing — ở đây đơn giản replace nhiều space thành underscore nếu cần
    # giữ letters, digits, underscore và space, dash sẽ trở thành underscore
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = s.strip()
    return s

def rel_type_safe(rel: str) -> str:
    """Chuyển predicate thành REL_TYPE hợp lệ: uppercase, spaces -> underscores, non-alnum -> underscore"""
    if rel is None:
        return "RELATED_TO"
    s = sanitize_identifier(rel)
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^\w]", "_", s)
    s = s.upper()
    if not s:
        return "RELATED_TO"
    return s

class Neo4jLoader:
    def __init__(self, uri, username, password):
        self.uri = uri
        self.username = username
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            # verify connectivity early so error surfaces here
            self.driver.verify_connectivity()
            print(f"[OK] Connected to Neo4j at {uri} as {username}")
        except exceptions.ServiceUnavailable as e:
            raise RuntimeError(f"Could not connect to Neo4j at {uri}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create Neo4j driver: {e}")

    def close(self):
        if getattr(self, "driver", None):
            self.driver.close()

    def create_entity(self, tx, entity):
        """Tạo node từ entity (labels + properties)"""
        labels = entity.get("label", ["Entity"])
        # sanitize labels and escape with backticks
        safe_labels = [f"`{sanitize_identifier(l)}`" for l in labels if l]
        labels_cypher = ":".join(safe_labels) if safe_labels else "`Entity`"

        base_set = [
            "n.id = $id",
            "n.name = $name",
            "n.description = $description",
            "n.original_text = $original_text"
        ]
        params = {
            "id": entity["id"],
            "name": entity.get("name", entity["id"]),
            "description": entity.get("description", ""),
            "original_text": entity.get("original_text", "")
        }

        # dynamic properties
        prop_assigns = []
        if "properties" in entity and isinstance(entity["properties"], dict):
            for key, value in entity["properties"].items():
                safe_key = sanitize_identifier(key).replace(" ", "_").replace("-", "_")
                if not safe_key:
                    continue
                param_name = f"prop__{safe_key}"
                prop_assigns.append(f"n.`{safe_key}` = ${param_name}")
                params[param_name] = value

        # metadata
        if "metadata" in entity:
            params["__metadata"] = json.dumps(entity["metadata"], ensure_ascii=False)
            base_set.append("n.metadata = $__metadata")

        set_clause = ",\n            ".join(base_set + prop_assigns)
        query = f"""
        CREATE (n:{labels_cypher})
        SET {set_clause}
        """
        tx.run(query, **params)

    def create_relationship_apoc(self, tx, triplet):
        """Tạo relationship bằng APOC (nếu APOC được cài)"""
        query = """
        MATCH (a {id: $subject_id})
        MATCH (b {id: $object_id})
        CALL apoc.create.relationship(a, $predicate, $properties, b) YIELD rel
        RETURN rel
        """
        properties = dict(triplet.get("properties", {}))
        if "metadata" in triplet:
            properties["metadata"] = json.dumps(triplet["metadata"], ensure_ascii=False)
        tx.run(query,
               subject_id=triplet["subject_id"],
               object_id=triplet["object_id"],
               predicate=triplet["predicate"],
               properties=properties)

    def create_relationship_native(self, tx, triplet):
        """Tạo relationship không cần APOC bằng cách inject REL TYPE đã sanitize.
           Vì REL TYPE phải là literal (không thể là parameter), ta sanitize thật kỹ trước khi inject.
        """
        rel_type = rel_type_safe(triplet.get("predicate", "RELATED_TO"))
        properties = dict(triplet.get("properties", {}))
        if "metadata" in triplet:
            properties["metadata"] = json.dumps(triplet["metadata"], ensure_ascii=False)

        # dùng parameter map $props
        query = f"""
        MATCH (a {{id: $subject_id}})
        MATCH (b {{id: $object_id}})
        CREATE (a)-[r:`{rel_type}` $props]->(b)
        RETURN r
        """
        tx.run(query,
               subject_id=triplet["subject_id"],
               object_id=triplet["object_id"],
               props=properties)

    def has_apoc(self):
        """Kiểm tra nhanh xem APOC có tồn tại không (simple test)."""
        try:
            with self.driver.session() as s:
                result = s.run("RETURN exists((:_) ) AS x")  # trivial, just to ensure call works
                # now test for apoc procedure existence
                res = s.run("CALL dbms.procedures() YIELD name WHERE name = 'apoc.create.relationship' RETURN count(*) as c").single()
                return bool(res and res["c"] > 0)
        except Exception:
            return False

    def load_data_from_json(self, json_file):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Clear old data (optional)
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("[INFO] Deleted old graph data")

        # Create entities (batching small to avoid giant tx)
        entities = data.get("entities", [])
        print(f"[INFO] Creating {len(entities)} entities...")
        with self.driver.session() as session:
            for e in entities:
                try:
                    session.execute_write(self.create_entity, e)
                except Exception as ex:
                    print(f"[ERROR] create_entity failed for {e.get('id')}: {ex}")

        # Relationships
        triplets = data.get("triplets", [])
        print(f"[INFO] Creating {len(triplets)} relationships...")
        use_apoc = self.has_apoc()
        if use_apoc:
            print("[INFO] APOC detected: will use apoc.create.relationship")
        else:
            print("[INFO] APOC not detected: will use native CREATE with sanitized relationship types")

        with self.driver.session() as session:
            for t in triplets:
                try:
                    if use_apoc:
                        session.execute_write(self.create_relationship_apoc, t)
                    else:
                        session.execute_write(self.create_relationship_native, t)
                except Exception as ex:
                    print(f"[ERROR] create_relationship failed for {t.get('subject_id')} -> {t.get('object_id')}: {ex}")

if __name__ == "__main__":
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD", "StrongPass123!")

    loader = None
    try:
        loader = Neo4jLoader(uri=uri, username=user, password=pwd)
        loader.load_data_from_json("graph_documents_v3.json")
        print("[DONE] Load finished")
    except Exception as e:
        print(f"[FATAL] {e}")
    finally:
        if loader:
            loader.close()
