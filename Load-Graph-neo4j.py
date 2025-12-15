import json
import os
import re
from neo4j import GraphDatabase, exceptions
from dotenv import load_dotenv

load_dotenv()

def sanitize_identifier(s: str) -> str:
    """Giữ lại letters, digits, underscore, space, dash, dấu tiếng Việt."""
    if s is None:
        return ""
    s = str(s)
    s = s.replace("`", "")
    s = re.sub(r"[^\w\s\-àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễ"
               r"ìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữ"
               r"ỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄ"
               r"ÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮ"
               r"ỲÝỴỶỸĐ]", "", s, flags=re.UNICODE)
    return s.strip()

def rel_type_safe(rel: str) -> str:
    """Predicate → REL_TYPE hợp lệ."""
    if rel is None:
        return "RELATED_TO"
    s = sanitize_identifier(rel)
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^\w]", "_", s)
    return s.upper() or "RELATED_TO"


class Neo4jLoader:
    def __init__(self, uri, username, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            self.driver.verify_connectivity()
            print(f"[OK] Connected to Neo4j Aura at {uri}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect: {e}")

    def close(self):
        if hasattr(self, "driver"):
            self.driver.close()

    # --------------------------------------------------------
    # ENTITY
    # --------------------------------------------------------
    def _serialize_value(self, v):
        """
        Serialize a value for Neo4j.
        Neo4j only accepts primitive types (str, int, float, bool) or arrays of primitives.
        Complex types (dict, list of dicts) must be converted to JSON strings.
        """
        if v is None:
            return None
        if isinstance(v, dict):
            # Dict must be serialized to JSON string
            return json.dumps(v, ensure_ascii=False)
        if isinstance(v, list):
            # Check if list contains complex types
            if len(v) > 0 and isinstance(v[0], dict):
                # List of dicts -> JSON string
                return json.dumps(v, ensure_ascii=False)
            # List of primitives is OK for Neo4j
            # But ensure all elements are primitives
            serialized = []
            for item in v:
                if isinstance(item, (dict, list)):
                    serialized.append(json.dumps(item, ensure_ascii=False))
                else:
                    serialized.append(item)
            return serialized
        # Primitive types (str, int, float, bool) are OK
        return v
    
    def create_entity(self, tx, entity):
        labels = entity.get("label", ["Entity"])
        safe_labels = [f"`{sanitize_identifier(l)}`" for l in labels if l]
        label_str = ":".join(safe_labels)

        # original_text may be list
        original_text = entity.get("original_text", "")
        if isinstance(original_text, list):
            original_text = json.dumps(original_text, ensure_ascii=False)

        metadata = entity.get("metadata", {})
        properties = entity.get("properties", {})

        params = {
            "id": entity["id"],
            "description": entity.get("description", ""),
            "original_text": original_text,
            "metadata": json.dumps(metadata, ensure_ascii=False) if metadata else None
        }

        set_clauses = [
            "n.id = $id",
            "n.description = $description",
            "n.original_text = $original_text",
        ]
        if metadata:
            set_clauses.append("n.metadata = $metadata")

        # dynamic properties - serialize complex types
        for k, v in properties.items():
            safe_k = sanitize_identifier(k).replace(" ", "_").replace("-", "_")
            if not safe_k:
                continue
            p = f"prop__{safe_k}"
            set_clauses.append(f"n.`{safe_k}` = ${p}")
            # Serialize complex values (dict, list of dicts) to JSON string
            params[p] = self._serialize_value(v)

        query = f"""
        CREATE (n:{label_str})
        SET {", ".join(set_clauses)}
        """
        tx.run(query, **params)

    # --------------------------------------------------------
    # RELATIONSHIP
    # --------------------------------------------------------
    def create_relationship(self, tx, triplet):
        rel_type = rel_type_safe(triplet.get("predicate"))
        props = triplet.get("properties", {})
        metadata = triplet.get("metadata", {})

        # combine props + metadata, serialize complex values
        payload = {}
        for k, v in props.items():
            payload[k] = self._serialize_value(v)
        if metadata:
            payload["metadata"] = json.dumps(metadata, ensure_ascii=False)

        query = f"""
        MATCH (a {{id: $sid}})
        MATCH (b {{id: $oid}})
        CREATE (a)-[r:`{rel_type}` $props]->(b)
        RETURN r
        """
        tx.run(query,
               sid=triplet["subject_id"],
               oid=triplet["object_id"],
               props=payload)

    # --------------------------------------------------------
    # MAIN LOADER
    # --------------------------------------------------------
    def load_data(self, json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entities = data.get("entities", [])
        # Support both "triplets" and "relationships" keys
        relationships = data.get("relationships", []) or data.get("triplets", [])

        # 1️⃣ Clear old graph
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
            print("[INFO] Deleted old KG")

        # 2️⃣ Load entities
        print(f"[INFO] Creating {len(entities)} entities…")
        with self.driver.session() as s:
            for i, e in enumerate(entities, 1):
                try:
                    s.execute_write(self.create_entity, e)
                except Exception as ex:
                    print(f"[ERROR][Entity] {e.get('id')}: {ex}")

        # 3️⃣ Load relationships
        print(f"[INFO] Creating {len(relationships)} relationships…")
        with self.driver.session() as s:
            for i, t in enumerate(relationships, 1):
                try:
                    s.execute_write(self.create_relationship, t)
                except Exception as ex:
                    print(f"[ERROR][Rel] {t.get('subject_id')} → {t.get('object_id')}: {ex}")

        print("[DONE] Load completed")


# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
if __name__ == "__main__":
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://5f398723.databases.neo4j.io")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "dM2Ld3cJ3mEn9WfFlP1_W3OXAUrstCbKPkGbtkDSHpE")

    json_file = "outputs/kg/knowledge_graph_historical_v5.json"

    loader = Neo4jLoader(
        uri=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD
    )

    try:
        loader.load_data(json_file)
    finally:
        loader.close()
