import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain

css = '''
<style>
.chat-message {
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-end;
}
.chat-message.user {
    background-color: #DCF8C6;
    justify-content: flex-end;
}
.chat-message.bot {
    background-color: #E5E5EA;
    justify-content: flex-start;
}
.chat-message .avatar {
    width: 20%;
}
.chat-message .avatar img {
    max-width: 78px;
    max-height: 78px;
    border-radius: 50%;
    object-fit: cover;
}
.chat-message .message {
    width: 80%;
    padding: 0 1.5rem;
    color: #000;
}
</style>
'''

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://i.ibb.co/cN0nmSj/Screenshot-2023-05-28-at-02-37-21.png" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://i.ibb.co/rMcg7sY/unnamed.jpg">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks, api_key):
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore, api_key):
    llm = ChatOpenAI(openai_api_key=api_key)
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Chat with multiple PDFs",
                       page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("Chat with multiple PDFs :books:")
    user_question = st.chat_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        # Add a Markdown component to display the greeting
        st.markdown(" Hi there, My name is Ashadullah Danish, This app is developed by me and this very early stage product if you have any feedback or suggestion please let me know.")

        links_row = "<a href='https://www.linkedin.com/in/ashadullah-danish/' target='_blank'>" \
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

        # Display the links row using Markdown
        st.markdown(links_row, unsafe_allow_html=True)

        # Function to increment view count
        def increment_views():
            # Read current view count from file
            try:
                with open("view_count.txt", "r") as file:
                    views = int(file.read())
            except FileNotFoundError:
                # If file doesn't exist, initialize view count to 0
                views = 0

            # Increment view count
            views += 1

            # Write updated view count to file
            with open("view_count.txt", "w") as file:
                file.write(str(views))

            return views

        # Increment view count only once per user visit
        if not st.session_state.get("view_counted", False):
            total_views = increment_views()
            st.session_state.view_counted = True
        else:
            total_views = int(open("view_count.txt", "r").read())

        # Display total views
        st.write("Total Views:", total_views)

        st.subheader("Your documents")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'", accept_multiple_files=True)

        model_options = ["OpenAI", "Hugging Face"]
        selected_model = st.selectbox("Select a model", model_options)
        if selected_model == "OpenAI":
            api_key = st.text_input("OpenAI API Key")
        elif selected_model == "Hugging Face":
            # api_key = st.text_input("Hugging Face API Key")
            st.write("This app currently works with OpenAI only due to hardware constraints on Streamlit. Running open-source models on Streamlit can be very costly. However, you can run it on your PC by downloading the code and uncommenting the line.")
        if st.button("Process"):
            with st.spinner("Processing"):
                # get pdf text
                raw_text = get_pdf_text(pdf_docs)

                # get the text chunks
                text_chunks = get_text_chunks(raw_text)

                # create vector store
                vectorstore = get_vectorstore(text_chunks, api_key)

                # create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore, api_key)
                st.write("Processing completed successfully!")

if __name__ == '__main__':
    main()
