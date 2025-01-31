import streamlit as st
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.messages import AIMessage, HumanMessage
from typing import List, Optional, Dict, Any

def get_pdf_text(pdf_docs: List[st.runtime.uploaded_file_manager.UploadedFile]) -> str:
    """
    Extract text from uploaded PDF files.
    
    Args:
        pdf_docs (List[UploadedFile]): List of uploaded PDF files
    
    Returns:
        str: Concatenated text from all PDF pages
    """
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            st.error(f"Error reading PDF {pdf.name}: {e}")
    return text

def get_text_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into manageable chunks.
    
    Args:
        text (str): Input text to be split
        chunk_size (int): Size of each text chunk
        chunk_overlap (int): Overlap between chunks
    
    Returns:
        List[str]: List of text chunks
    """
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    return text_splitter.split_text(text)

def get_vectorstore(text_chunks: List[str], embeddings_config: Dict[str, Any]) -> FAISS:
    """
    Create a vector store from text chunks.
    
    Args:
        text_chunks (List[str]): List of text chunks
        embeddings_config (dict): Configuration for embeddings
    
    Returns:
        FAISS: Vector store of text embeddings
    """
    try:
        # Select embeddings based on configuration
        if embeddings_config['type'] == 'OpenAI':
            embeddings = OpenAIEmbeddings(
                openai_api_key=embeddings_config['api_key']
            )
        elif embeddings_config['type'] == 'HuggingFace':
            embeddings = HuggingFaceEmbeddings(
                model_name=embeddings_config.get(
                    'model', 
                    'sentence-transformers/all-MiniLM-L6-v2'
                )
            )
        else:
            st.error(f"Unsupported embeddings type: {embeddings_config['type']}")
            return None
        
        # Create vector store
        vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
        return vectorstore
    except Exception as e:
        st.error(f"Error creating vector store: {e}")
        return None

def get_conversation_chain(vectorstore, model_config: dict):
    """
    Create a conversational retrieval chain.
    
    Args:
        vectorstore (FAISS): Vector store of document embeddings
        model_config (dict): Configuration for the language model
    
    Returns:
        ConversationalRetrievalChain: Conversation chain for Q&A
    """
    try:
        # Select LLM based on model type
        if model_config['type'] == 'OpenAI':
            llm = ChatOpenAI(
                openai_api_key=model_config['api_key'], 
                model=model_config.get('model', 'gpt-3.5-turbo')
            )
        elif model_config['type'] == 'Groq':
            llm = ChatGroq(
                groq_api_key=model_config['api_key'],
                model_name=model_config.get('model', 'llama-2-70b-4096')
            )
        else:
            st.error("Unsupported model type")
            return None

        # Create conversation chain
        memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
        conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            memory=memory
        )
        return conversation_chain
    except Exception as e:
        st.error(f"Error creating conversation chain: {e}")
        return None

def handle_userinput(user_question: str):
    """
    Process user input and display chat history.
    
    Args:
        user_question (str): User's input question
    """
    if not st.session_state.conversation:
        st.warning("Please upload and process PDFs first.")
        return

    try:
        # Append user message to chat history
        st.session_state.chat_history.append(HumanMessage(content=user_question))

        # Get response from conversation chain
        response = st.session_state.conversation.invoke({'question': user_question})
        new_messages = response['chat_history']

        # Display messages
        for message in new_messages:
            if isinstance(message, AIMessage):
                with st.chat_message("AI"):
                    st.markdown(message.content)
            elif isinstance(message, HumanMessage):
                with st.chat_message("Human"):
                    st.markdown(message.content)

        # Update session state chat history
        st.session_state.chat_history.extend(new_messages)
    except Exception as e:
        st.error(f"Error processing user input: {e}")

def main():
    """
    Main Streamlit application function
    """
    # Set page configuration
    st.set_page_config(
        page_title="Multi-PDF Chat Assistant", 
        page_icon=":books:", 
        layout="wide"
    )

    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Main application title
    st.title("📚 Multi-PDF Chat Assistant")
    
    # User input section
    user_question = st.chat_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    # Sidebar layout
    with st.sidebar:
        # Greeting and introduction
        st.markdown("## About the App")
        st.info("Hi there, My name is Ashadullah Danish, This app is developed by me and this very early stage product if you have any feedback or suggestion please let me know.")

        # Social links
        links_row = ("<a href='https://www.linkedin.com/in/ashadullah-danish' target='_blank'>" \
                    "<img src='https://img.icons8.com/color/48/000000/linkedin.png' width='30'></a>" \
                    " | " \
                    "<a href='https://github.com/AshadullahDanish' target='_blank'>" \
                    "<img src='https://img.icons8.com/color/48/000000/github.png' width='30'></a>" \
                    " | " \
                    "<a href='https://www.kaggle.com/ashadullah' target='_blank'>" \
                    "<img src='https://www.kaggle.com/static/images/site-logo.png' width='30'></a>" \
                    " | " \
                    "<a href='https://ashadullahdanish.netlify.app/' target='_blank'>" \
                    "<img src='https://img.icons8.com/color/48/000000/globe--v1.png' width='30'></a>"
        )
        st.markdown(links_row, unsafe_allow_html=True)

        # PDF Upload Section
        st.subheader("📄 Upload PDF Documents")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here", 
            type=['pdf'], 
            accept_multiple_files=True
        )

        # Model Selection
        st.subheader("🤖 Model Configuration")
        selected_model = st.selectbox(
            "Select AI Model", 
            [
                "OpenAI GPT-3.5 Turbo", 
                "Groq Llama2 70B", 
                "Groq Mixtral 8x7B",
                "Groq Gemma 7B"
            ]
        )

        # Embeddings Selection
        st.subheader("🧩 Embeddings")
        selected_embeddings = st.selectbox(
            "Select Embeddings", 
            ["OpenAI", "HuggingFace"]
        )

        # Model-specific configurations
        if selected_model == "OpenAI GPT-3.5 Turbo":
            model_api_key = st.text_input(
                "OpenAI API Key", 
                type="password", 
                help="Required for processing PDFs with OpenAI's model"
            )
            model_config = {
                'type': 'OpenAI',
                'api_key': model_api_key,
                'model': 'gpt-3.5-turbo'
            }
        elif selected_model == "Groq Llama2 70B":
            model_api_key = st.text_input(
                "Groq API Key", 
                type="password", 
                help="Required for processing PDFs with Groq's Llama2 model"
            )
            model_config = {
                'type': 'Groq',
                'api_key': model_api_key,
                'model': 'llama-2-70b-4096'
            }
        elif selected_model == "Groq Mixtral 8x7B":
            model_api_key = st.text_input(
                "Groq API Key", 
                type="password", 
                help="Required for processing PDFs with Groq's Mixtral model"
            )
            model_config = {
                'type': 'Groq',
                'api_key': model_api_key,
                'model': 'mixtral-8x7b-32768'
            }
        elif selected_model == "Groq Gemma 7B":
            model_api_key = st.text_input(
                "Groq API Key", 
                type="password", 
                help="Required for processing PDFs with Groq's Gemma model"
            )
            model_config = {
                'type': 'Groq',
                'api_key': model_api_key,
                'model': 'gemma-7b-it'
            }

        # Embeddings-specific configurations
        if selected_embeddings == "OpenAI":
            embeddings_api_key = st.text_input(
                "OpenAI API Key for Embeddings", 
                type="password", 
                help="Required for generating embeddings"
            )
            embeddings_config = {
                'type': 'OpenAI',
                'api_key': embeddings_api_key
            }
        elif selected_embeddings == "HuggingFace":
            huggingface_model = st.selectbox(
                "Select HuggingFace Model", 
                [
                    "sentence-transformers/all-MiniLM-L6-v2",
                    "sentence-transformers/all-mpnet-base-v2",
                    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                ]
            )
            embeddings_config = {
                'type': 'HuggingFace',
                'model': huggingface_model
            }
        
        # Process Button
        if st.button("Process PDFs", type="primary"):
            # Validate inputs
            if not pdf_docs:
                st.warning("Please upload PDF documents.")
                return
            
            if not model_api_key:
                st.warning("Please enter a Model API Key.")
                return

            with st.spinner("Processing documents..."):
                try:
                    # Extract text from PDFs
                    raw_text = get_pdf_text(pdf_docs)
                    
                    # Split text into chunks
                    text_chunks = get_text_chunks(raw_text)
                    
                    # Create vector store
                    vectorstore = get_vectorstore(text_chunks, embeddings_config)
                    
                    if vectorstore:
                        # Create conversation chain
                        st.session_state.conversation = get_conversation_chain(vectorstore, model_config)
                        st.success("Documents processed successfully!")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == '__main__':
    main()