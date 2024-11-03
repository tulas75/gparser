import os
import time
from langchain_community.embeddings import InfinityEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Pinecone Configuration
#PINECONE_API_KEY = os.environ['PINECONE_API_KEY']

embeddings = InfinityEmbeddings(
    model="BAAI/bge-m3",
    infinity_api_url="http://192.168.1.8:7997",
)

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
