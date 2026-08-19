def split_text(
        text: str,
        chunk_size: int = 200
):
    chunks = []

    current_chunk = ""


    paragraphs = text.split("\n")


    for paragraph in paragraphs:

        paragraph = paragraph.strip()


        if not paragraph:
            continue


        # 如果当前块加上新段落没有超过限制
        if len(current_chunk) + len(paragraph) < chunk_size:

            current_chunk += paragraph + "\n"


        else:

            # 保存当前块
            if current_chunk:
                chunks.append(current_chunk)


            # 开始新的块
            current_chunk = paragraph + "\n"


    # 保存最后一个块
    if current_chunk:
        chunks.append(current_chunk)


    return chunks