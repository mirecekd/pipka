# Principal
import streamlit as st
import interpreter


# st components
from st_components.st_init import set_style
from st_components.st_session_states import init_session_states
from st_components.st_sidebar import st_sidebar
from st_components.st_main import st_main

#validation
from litellm import completion
set_style()
st.title("PIPKA")
init_session_states()
st_sidebar()
st_main()
