import os
import time
from langchain_community.embeddings import InfinityEmbeddings
from langchain_community.embeddings import DeepInfraEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

embeddings = InfinityEmbeddings(
    model="BAAI/bge-m3",
    infinity_api_url="http://192.168.1.8:7997",
)

#embeddings = DeepInfraEmbeddings(
#    model_id="BAAI/bge-m3",
##    query_instruction="",
#    embed_instruction="",
#    deepinfra_api_token=os.environ['DEEPINFRA_API_KEY']
#)

def get_vector_store(index_name, namespace):
    """
    Create and return a PineconeVectorStore instance
    Args:
        index_name (str): Name of the Pinecone index to use
        namespace (str): Namespace for the vector store
    Returns:
        PineconeVectorStore: Configured vector store instance
    """
    pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
    index = pc.Index(index_name)
    
    return PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)

def get_vector_store_pg(db,collection_name):
    """
    Create and return a PgVectorStore instance
    Args:
        db (str): Name of the Postgres db to use
        colletion_name (str): Table for the vector store
    Returns:
        PgVectorStore: Configured vector store instance
    """
    connection = "postgresql+psycopg://langchain:langchain@localhost:6024/"+db  # Uses psycopg3!
    collection_name = collection_name
    return PGVector(connection=connection, collection_name=collection_name, embeddings=embeddings, use_jsonb=True)
