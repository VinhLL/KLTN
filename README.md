# Vietnamese History Knowledge Graph & RAG System

This project focuses on constructing a **Knowledge Graph (KG)** from Vietnamese History textbooks (specifically Grade 12) and implementing a **Retrieval-Augmented Generation (RAG)** system to answer questions based on the constructed graph.

## 🚀 Overview

The system processes unstructured text from textbooks to extract entities and relationships, building a structured Knowledge Graph. This graph is then loaded into a **Neo4j** database. A RAG pipeline is implemented to query this knowledge base, providing accurate answers to history-related questions.

## 📂 Project Structure

- **`SGK/`**: Contains the source documents (e.g., `SGK_Lich_Su_12_Ket_Noi_Tri_Thuc.txt`) and related assets.
- **`outputs/`**: Directory for generated output files.
- **`kb-kg.ipynb`**: The main Jupyter Notebook for Knowledge Graph construction, RAG implementation, and evaluation.
- **`buildkg.ipynb` / `buildkg_v2.ipynb`**: Alternative/Previous versions of the graph building process.
- **`load_neo4j.py`**: Python script to load the generated graph data (JSON format) into a Neo4j database.
- **`graph_documents_*.json` / `.ttl`**: The generated Knowledge Graph data in JSON and Turtle formats.
- **`RAG Evaluation Report.html`**: Report containing the evaluation metrics of the RAG system.

## 🛠️ Prerequisites

- **Python 3.8+**
- **Neo4j Database**: You need a running instance of Neo4j (Desktop or AuraDB).
- **GPU**: Recommended for running Large Language Models (LLMs) for extraction and RAG.

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd KLTN
    ```

2.  **Install dependencies:**
    The project relies on several Python libraries including `langchain`, `transformers`, `neo4j`, and `sentence-transformers`.
    ```bash
    pip install langchain langchain-community transformers sentence-transformers faiss-cpu neo4j python-dotenv accelerate bitsandbytes
    ```

3.  **Environment Setup:**
    Create a `.env` file in the root directory to configure your Neo4j credentials:
    ```env
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=your_password
    ```

## 🏃‍♂️ Usage

### 1. Construct the Knowledge Graph
Open and run the cells in `kb-kg.ipynb` (or `buildkg_v2.ipynb`). This notebook contains the logic to:
- Read the textbook data.
- Use an LLM to extract entities and relationships.
- Save the graph data to `graph_documents_v3.json`.

### 2. Load Data into Neo4j
Once the JSON graph data is generated, use the provided script to import it into your Neo4j database:

```bash
python load_neo4j.py
```
*Note: This script will clear existing data in the database before loading the new graph.*

### 3. Run RAG & Evaluation
The `kb-kg.ipynb` notebook also contains the RAG pipeline. Run the relevant sections to:
- Initialize the GraphRAG system.
- Query the system with natural language questions.
- Evaluate the performance using the provided test sets (`questions_500.txt`, `question_1000.txt`).

## 📊 Evaluation

The system includes an evaluation module that generates reports (e.g., `RAG Evaluation Report.html`) assessing the accuracy and relevance of the answers provided by the RAG system.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
