# PROJECT STRUCTURE
In the Thoth project there are 5 main folders:
- thoth_be: contains the backend code as a Django application
- thoth_sl: contains the frontend code in Streamlit
- thoth_sqldb2: contains the database management code with specific Thoth APIs
- thoth_vdb2: contains the vector database management code with specific Thoth APIs
- thoth_docs contains the documentation

When you find an issue that can be fixed modifying thoth_sqldb2 or thoth_vdb2, please do not try any workaround, fix the library and then update the requirements.txt file in thoth_be and thoth_sl.

## thoth_sqldb2
This library provides the database management functionality. 
You can find the sources [here](https://github.com/mptyl/thoth_sqldb2)
I give you the permission to manage this library modifying the code, creating PRs, merging them, releasing new versions, etc.
The library is published on PyPi [here](https://pypi.org/project/thoth_vdb2/).
If you need to publish, build, after changing the version last number, and twine using the token in pypi_token file

## thoth_vdbmanager
This library provides the vector database management functionality. 
You can find the sources [here](https://github.com/mptyl/thoth_vdbmanager)
I give you the permission to manage this library modifying the code, creating PRs, merging them, releasing new versions, etc.
The library is published on PyPi [here](https://pypi.org/project/thoth-vdbmanager/).
If you need to publish, build, after changing the version last number, and twine using the token in pypi_token file