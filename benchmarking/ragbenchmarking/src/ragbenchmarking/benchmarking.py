import ast
import streamlit as st
import requests

st.set_page_config(layout="wide") # Optional: Use wide layout

st.title("Knowledge Base Management Dashboard")

# Global collection name input
collection_name = st.text_input('Enter the name of the collection for ingestion and retrieval', value="my_collection")

# Tabs for different functionalities
raw_text_tab, pdf_tab, website_tab, ask_retrieve_tab = st.tabs(['Raw Text', 'PDF', 'Website', 'Ask/Retrieve'])

# --- Ingestion Tabs ---

with raw_text_tab:
    st.header("Add Raw Text to Knowledge Base")
    with st.form('RAW TEXT FORM'):
        raw_text = st.text_area('Enter the text you want to add')
        chunk_size_raw = st.number_input('Optional: Enter chunk size (default from config)', min_value=1, value=None, key="raw_chunk_size")

        if st.form_submit_button('Submit Raw Text', use_container_width=True):
            if not collection_name:
                st.error("Please enter a collection name.")
            elif not raw_text:
                st.error("Please enter text to add.")
            else:
                with st.spinner(
                    text=f'Adding Text to "{collection_name}" Knowledge Base...',
                    show_time=True
                ):
                    payload = {
                        'raw-text': raw_text,
                        'collection-name': collection_name
                    }
                    if chunk_size_raw:
                        payload['chunk-size'] = chunk_size_raw

                    try:
                        response = requests.post(
                            url='http://localhost:9001/add-raw-text',
                            json=payload
                        )

                        if response.status_code == 200:
                            st.success('Added Text to Knowledge Base successfully!')
                            st.info(f'{response.json()["chunks-count"]} chunks added.')
                        else:
                            st.error(f"Error adding raw text: {response.status_code}")
                            st.json(response.json())
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the API. Please ensure the FastAPI application is running at http://localhost:9001.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")


with pdf_tab:
    st.header("Upload PDF to Knowledge Base")
    with st.form('Upload PDF FORM'):
        uploaded_file = st.file_uploader('Upload PDF file', type='pdf')
        chunk_size_pdf = st.number_input('Optional: Enter chunk size (default from config)', min_value=1, value=None, key="pdf_chunk_size")


        if st.form_submit_button('Submit PDF', use_container_width=True):
            if not collection_name:
                st.error("Please enter a collection name.")
            elif uploaded_file is None:
                st.error("Please upload a PDF file.")
            else:
                # Save the uploaded file temporarily
                temp_pdf_path = 'temp_uploaded.pdf'
                with open(temp_pdf_path, "wb") as file:
                    file.write(uploaded_file.getbuffer())

                with st.spinner(
                    text=f'Adding PDF data to "{collection_name}" Knowledge Base...',
                    show_time=True
                ):
                    payload = {
                        'pdf': '/teamspace/studios/this_studio/vxp-agent-backend/benchmarking/ragbenchmarking/temp_uploaded.pdf', # Pass the path to the FastAPI service
                        'collection-name': collection_name
                    }
                    if chunk_size_pdf:
                        payload['chunk-size'] = chunk_size_pdf

                    try:
                        response = requests.post(
                            url='http://localhost:9001/add-pdf',
                            json=payload
                        )

                        if response.status_code == 200:
                            st.success('Added PDF Data to Knowledge Base successfully!')
                            st.info(f'{response.json()["chunks-count"]} chunks added.')
                        else:
                            st.error(f"Error adding PDF: {response.status_code}")
                            st.json(response.json())
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the API. Please ensure the FastAPI application is running at http://localhost:9001.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")


with website_tab:
    st.header("Add Website Content to Knowledge Base")
    with st.form('Website FORM'):
        website_url = st.text_input('Enter the URL of the website')
        chunk_size_website = st.number_input('Optional: Enter chunk size (default from config)', min_value=1, value=None, key="website_chunk_size")


        if st.form_submit_button('Submit Website', use_container_width=True):
            if not collection_name:
                st.error("Please enter a collection name.")
            elif not website_url:
                st.error("Please enter a website URL.")
            else:
                with st.spinner(
                    text=f'Adding Website data to "{collection_name}" Knowledge Base...',
                    show_time=True
                ):
                    payload = {
                        'website': website_url,
                        'collection-name': collection_name
                    }
                    if chunk_size_website:
                        payload['chunk-size'] = chunk_size_website

                    try:
                        response = requests.post(
                            url='http://localhost:9001/add-website',
                            json=payload
                        )

                        if response.status_code == 200:
                            st.success('Added Website Data to Knowledge Base successfully!')
                            st.info(f'{response.json()["chunks-count"]} chunks added.')
                        else:
                            st.error(f"Error adding website: {response.status_code}")
                            st.json(response.json())
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the API. Please ensure the FastAPI application is running at http://localhost:9001.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")


# --- Ask/Retrieve Tab ---

with ask_retrieve_tab:
    st.header("Retrieve Information from Knowledge Base")
    with st.form('RETRIEVE FORM'):
        query = st.text_area('Enter your query', height=100)
        # Using the globally defined collection_name, but also allowing override if needed
        # For simplicity, we'll just use the global one for now.
        # collection_name_retrieve = st.text_input('Collection Name (can override global)', value=collection_name, key="retrieve_collection_name")
        limit = st.number_input('Limit (number of results)', min_value=1, value=5)
        milvus_filter = st.text_input('Milvus Filter (e.g., "id > 100")', help="Milvus filter expression, e.g., 'source == \"website\"'")
        output_fields = st.text_input('Output Fields (comma-separated, e.g., "id,text,source")', value="id,text,source")


        if st.form_submit_button('Retrieve Documents', use_container_width=True):
            if not collection_name:
                st.error("Please enter a collection name in the global input.")
            elif not query:
                st.error("Please enter a query.")
            else:
                with st.spinner(
                    text=f'Searching "{collection_name}" for "{query}"...',
                    show_time=True
                ):
                    payload = {
                        'query': query,
                        'collection-name': collection_name,
                        'limit': limit,
                        'output-fields': [field.strip() for field in output_fields.split(',')] if output_fields else []
                    }
                    if milvus_filter:
                        payload['filter'] = milvus_filter

                    try:
                        response = requests.post(
                            url='http://localhost:9001/retrieve',
                            json=payload
                        )

                        if response.status_code == 200:
                            st.success('Retrieval successful!')
                            results = response.json()
                            if results:
                                st.subheader(f"Found {len(results)} document(s):")
                                # Display results in st.code or st.json
                                for i, doc in enumerate(results):
                                    st.markdown(f"--- Document {i+1} ---")
                                    # Use json.dumps for pretty printing within st.code
                                    st.json(ast.literal_eval(doc))
                            else:
                                st.info("No documents found matching your query and filters.")
                        else:
                            st.error(f"Error during retrieval: {response.status_code}")
                            st.json(response.json())
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the API. Please ensure the FastAPI application is running at http://localhost:9001.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")