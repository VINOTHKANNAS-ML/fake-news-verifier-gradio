"""Content ingestion agent - handles text extraction from all input types."""
from typing import Any, Dict
from app.agents.base import BaseAgent, AgentResult
from app.services.huggingface import HuggingFaceService
from app.services.assemblyai import AssemblyAIService
from app.services.url_extractor import URLExtractorService, URLExtractionError
from app.utils.text_processing import clean_text, extract_claims
import base64


class IngestionAgent(BaseAgent):
    """Agent responsible for ingesting and preprocessing content."""

    def __init__(self):
        super().__init__(
            name="IngestionAgent",
            description="Extracts and preprocesses text from text, image, audio, or URL inputs"
        )
        self.hf_service = HuggingFaceService()
        self.audio_service = AssemblyAIService()
        self.url_service = URLExtractorService()

    async def _process(self, context: Dict[str, Any]) -> AgentResult:
        input_type = context.get("input_type")
        content = context.get("content")
        file_data = context.get("file_data")

        extracted_text = ""
        metadata = {"input_type": input_type, "processing_steps": []}

        if input_type == "text":
            extracted_text = content or ""
            metadata["processing_steps"].append("direct_text_input")

        elif input_type == "image":
            image_bytes = base64.b64decode(file_data) if isinstance(file_data, str) else file_data
            caption = await self.hf_service.image_captioning(image_bytes)
            extracted_text = caption or ""
            metadata["processing_steps"].append("image_captioning")
            metadata["image_caption"] = caption

        elif input_type == "audio":
            audio_bytes = base64.b64decode(file_data) if isinstance(file_data, str) else file_data
            transcription = await self.audio_service.transcribe(audio_bytes)
            extracted_text = transcription or ""
            metadata["processing_steps"].append("audio_transcription")
            metadata["audio_duration"] = context.get("audio_duration")

        elif input_type == "url":
            source_url = (content or "").strip()
            try:
                article = await self.url_service.extract(source_url)
                title = article.get("title") or ""
                body = article.get("text") or ""
                extracted_text = f"{title}\n\n{body}".strip() if title else body
                metadata["processing_steps"].append("url_article_extraction")
                metadata["article_title"] = title
                metadata["article_author"] = article.get("author")
                metadata["article_publish_date"] = article.get("publish_date")
                metadata["article_domain"] = article.get("domain")
                metadata["source_url"] = article.get("source_url")
            except URLExtractionError as e:
                metadata["processing_steps"].append("url_extraction_failed")
                metadata["url_error"] = str(e)
                return AgentResult(
                    success=False,
                    data={"extracted_text": "", "claims": [], "original_input": source_url},
                    metadata=metadata,
                    error=str(e)
                )

        cleaned_text = clean_text(extracted_text)
        claims = extract_claims(cleaned_text)

        metadata["original_length"] = len(extracted_text)
        metadata["cleaned_length"] = len(cleaned_text)
        metadata["claims_extracted"] = len(claims)

        return AgentResult(
            success=True,
            data={
                "extracted_text": cleaned_text,
                "claims": claims,
                "original_input": content or "[file_upload]"
            },
            metadata=metadata
        )
