"""Controller for VSIC-to-MCC mapping CLI command (consumer-only).

Embeddings come from a pre-built `.npz` artifact (produced by `embed`); this
controller never constructs an embedding client. The LLM re-rank provider stays
dual (ollama | wokushop).
"""

from pathlib import Path
from typing import Optional

from loguru import logger
from tqdm import tqdm

from app.repositories.detail_mapping_xlsx_repository import DetailMappingXlsxRepository
from app.repositories.embedding_artifact_repository import EmbeddingArtifactRepository
from app.repositories.mapping_checkpoint_repository import (
    MappingCheckpointRepository as MappingCheckpointRepositoryImpl,
)
from app.repositories.ollama_llm_client import OllamaLLMClient
from app.repositories.wokushop_llm_client import WokuShopLLMClient
from app.repositories.simple_mapping_xlsx_repository import SimpleMappingXlsxRepository
from app.services.map_vsic_to_mcc_use_case import MapVsicToMccUseCase
from app.services.mcc_code_validator import MccCodeValidator
from app.services.ollama_health_check import check_ollama_llm

DEFAULT_TOP_K = 10


class MappingController:
    """Controller for orchestrating the mapping pipeline."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        llm_model: str = "qwen3.5:9b",
        template_path: Optional[Path] = None,
        llm_provider: str = "ollama",
        wokushop_api_key: Optional[str] = None,
        wokushop_base_url: str = "https://llm.wokushop.com/v1",
        wokushop_model: str = "gpt-4o",
    ) -> None:
        """
        Initialize controller with LLM provider configuration.

        Args:
            ollama_host: Ollama server URL (for the Ollama LLM provider).
            llm_model: LLM model name for the Ollama provider.
            template_path: Path to Excel template for detailed output.
            llm_provider: LLM provider name ("ollama" or "wokushop").
            wokushop_api_key: WokuShop API key.
            wokushop_base_url: WokuShop API base URL.
            wokushop_model: WokuShop LLM model name.
        """
        self.ollama_host = ollama_host
        self.llm_model = llm_model
        self.template_path = template_path
        self.llm_provider = llm_provider
        self.wokushop_api_key = wokushop_api_key
        self.wokushop_base_url = wokushop_base_url
        self.wokushop_model = wokushop_model

    def execute(
        self,
        embeddings: Path,
        output: Path,
        output_detail: Path,
        top_k: int = DEFAULT_TOP_K,
        resume: bool = False,
        limit: Optional[int] = None,
        gdrive_output_dir: Optional[Path] = None,
    ) -> int:
        """
        Execute the mapping pipeline.

        Args:
            embeddings: Path to the embedding artifact (.npz).
            output: Path to simple Excel output.
            output_detail: Path to detailed Excel output.
            top_k: Number of top candidate MCCs to send to LLM.
            resume: Whether to resume from checkpoint.
            limit: Maximum number of VSIC entries to process.
            gdrive_output_dir: Base directory on Google Drive for all outputs.

        Returns:
            Exit code (0 = success, 1 = artifact not found, 2 = LLM/Ollama error,
            3 = IO error, 4 = invalid artifact).
        """
        try:
            # Override paths if gdrive_output_dir is provided
            if gdrive_output_dir:
                if str(gdrive_output_dir).startswith("/content/drive"):
                    if not Path("/content/drive/MyDrive").exists():
                        logger.warning(
                            "Path starts with /content/drive but Google Drive "
                            "does not appear to be mounted. Output will be local."
                        )

                gdrive_output_dir.mkdir(parents=True, exist_ok=True)
                output = gdrive_output_dir / "vsic-mcc-mapping.xlsx"
                output_detail = gdrive_output_dir / "vsic-mcc-mapping-detail.xlsx"
                checkpoint_path = gdrive_output_dir / ".mapping-progress.json"
                if not embeddings.exists():
                    embeddings = gdrive_output_dir / "embed-artifact.npz"
                logger.info(f"Using Google Drive output directory: {gdrive_output_dir}")
            else:
                checkpoint_path = output.parent / ".mapping-progress.json"

            # Load the embedding artifact (sole source of vectors + text).
            try:
                artifact = EmbeddingArtifactRepository().read(embeddings)
            except FileNotFoundError as e:
                logger.error(f"Embedding artifact not found: {e}")
                return 1
            except ValueError as e:
                logger.error(f"Invalid embedding artifact: {e}")
                return 4

            logger.info(
                f"Loaded artifact: {len(artifact.mcc_codes)} MCC, "
                f"{len(artifact.vsic_codes)} VSIC entries"
            )

            # Health check (LLM only — embeddings come from the artifact).
            try:
                if self.llm_provider == "wokushop":
                    wokushop_client = WokuShopLLMClient(
                        api_key=self.wokushop_api_key,
                        base_url=self.wokushop_base_url,
                        model=self.wokushop_model,
                    )
                    if not wokushop_client.health_check():
                        logger.error("WokuShop LLM health check failed")
                        return 2
                else:
                    check_ollama_llm(self.ollama_host, self.llm_model)
            except RuntimeError as e:
                logger.error(f"Health check failed: {e}")
                return 2

            # Clamp top-k to rerank_top_n in the artifact metadata
            rerank_top_n = artifact.meta.get("rerank_top_n", 20)
            if top_k > rerank_top_n:
                logger.warning(
                    f"Requested --top-k {top_k} exceeds rerank_top_n ({rerank_top_n}) "
                    f"available in the artifact. Clamping to {rerank_top_n}."
                )
                llm_n = rerank_top_n
            else:
                llm_n = top_k

            # Initialize LLM client
            if self.llm_provider == "wokushop":
                logger.info(
                    f"Using WokuShop LLM provider with model: {self.wokushop_model}"
                )
                llm_client = WokuShopLLMClient(
                    api_key=self.wokushop_api_key,
                    base_url=self.wokushop_base_url,
                    model=self.wokushop_model,
                )
            else:
                logger.info(f"Using Ollama LLM provider with model: {self.llm_model}")
                llm_client = OllamaLLMClient(self.ollama_host, self.llm_model)

            checkpoint_repo = MappingCheckpointRepositoryImpl(checkpoint_path)
            validator = MccCodeValidator(list(artifact.mcc_codes))

            use_case = MapVsicToMccUseCase(
                llm_client=llm_client,
                checkpoint_repo=checkpoint_repo,
                artifact=artifact,
                validator=validator,
            )

            simple_repo = SimpleMappingXlsxRepository()
            if self.template_path:
                detail_repo = DetailMappingXlsxRepository(self.template_path)
            else:
                logger.warning("No template path provided, skipping detailed output")
                detail_repo = None

            total = (
                len(artifact.vsic_codes)
                if limit is None
                else min(limit, len(artifact.vsic_codes))
            )

            entries = []
            with tqdm(total=total, desc="Mapping VSIC to MCC") as pbar:
                for entry in use_case.execute(llm_n=llm_n, resume=resume, limit=limit):
                    entries.append(entry)
                    pbar.update(1)

            simple_repo.write(entries, output)
            logger.info(f"Wrote simple mapping to {output}")

            if detail_repo:
                detail_repo.write(entries, output_detail)
                logger.info(f"Wrote detailed mapping to {output_detail}")

            logger.info("Mapping pipeline completed successfully")
            return 0

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return 1
        except RuntimeError as e:
            if "Ollama" in str(e):
                logger.error(f"Ollama error: {e}")
                return 2
            logger.error(f"Runtime error: {e}")
            return 1
        except IOError as e:
            logger.error(f"IO error: {e}")
            return 3
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return 1
