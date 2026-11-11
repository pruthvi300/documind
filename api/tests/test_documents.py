import io

from tests.conftest import upload


async def test_upload_list_get_delete(client):
    response = await upload(client)
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["status"] == "indexed"
    assert doc["chunk_count"] == 1
    assert doc["uploaded_at"].endswith("Z") or "+00:00" in doc["uploaded_at"]

    listing = (await client.get("/api/documents")).json()
    assert listing["total"] == 1
    assert listing["documents"][0]["id"] == doc["id"]

    assert (await client.get(f"/api/documents/{doc['id']}")).json()["filename"] == "policy.txt"

    assert (await client.delete(f"/api/documents/{doc['id']}")).status_code == 204
    assert (await client.get(f"/api/documents/{doc['id']}")).status_code == 404
    assert client.store.search("Refunds are accepted within 30 days of purchase.") == []


async def test_rejects_unsupported_extension(client):
    response = await upload(client, name="virus.exe", content=b"MZ")
    assert response.status_code == 400


async def test_empty_document_is_422_and_leaves_nothing_behind(client, tmp_path):
    response = await upload(client, content=b"   \n\n  ")
    assert response.status_code == 422
    assert (await client.get("/api/documents")).json()["total"] == 0


async def test_too_large_upload_is_413(client, monkeypatch):
    from app.routes import documents

    monkeypatch.setattr(documents.settings, "MAX_FILE_SIZE_MB", 0)
    assert (await upload(client)).status_code == 413


async def test_invalid_uuid_is_422_not_500(client):
    assert (await client.get("/api/documents/not-a-uuid")).status_code == 422


async def test_csv_rows_become_labelled_text(client):
    response = await upload(client, name="prices.csv", content=b"plan,price\nbasic,10\npro,25\n", mime="text/csv")
    assert response.status_code == 201
    stored = client.store.vectorstore.get()["documents"]
    assert stored == ["plan: basic; price: 10\nplan: pro; price: 25"]


async def test_docx_upload(client):
    import docx

    buffer = io.BytesIO()
    d = docx.Document()
    d.add_paragraph("Warranty lasts two years.")
    d.save(buffer)
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    response = await upload(client, name="warranty.docx", content=buffer.getvalue(), mime=mime)
    assert response.status_code == 201, response.text


async def test_pdf_chunks_keep_page_numbers(client):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    for text in ("First page text", "Second page text"):
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)

    response = await upload(client, name="manual.pdf", content=buffer.getvalue(), mime="application/pdf")
    assert response.status_code == 201, response.text
    hit = client.store.search("Second page text", k=1)[0]
    assert hit["metadata"]["page_number"] == 2
