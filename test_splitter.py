from app.services.text_splitter import split_text


text = """
企业AI知识库助手是一套帮助企业管理内部资料的系统。
员工可以上传公司文档。
AI会自动解析文档内容。
然后进行知识检索。
"""


chunks = split_text(
    text,
    chunk_size=20
)


for index, chunk in enumerate(chunks):
    print("第", index + 1, "个文本块:")
    print(chunk)
    print("----------------")