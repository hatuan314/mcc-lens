"""Controller for VSIC-to-MCC mapping CLI command."""

import json
from pathlib import Path
from typing import Optional

from loguru import logger
from tqdm import tqdm

from app.repositories.detail_mapping_xlsx_repository import DetailMappingXlsxRepository
from app.repositories.mapping_checkpoint_repository import (
    MappingCheckpointRepository as MappingCheckpointRepositoryImpl,
)
from app.repositories.ollama_embedding_client import OllamaEmbeddingClient
from app.repositories.ollama_llm_client import OllamaLLMClient
from app.repositories.simple_mapping_xlsx_repository import SimpleMappingXlsxRepository
from app.services.map_vsic_to_mcc_use_case import MapVsicToMccUseCase
from app.services.mcc_code_validator import MccCodeValidator
from app.services.ollama_health_check import check_ollama_models


class MappingController:
    """Controller for orchestrating the mapping pipeline."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        llm_model: str = "qwen2.5:14b",
        embedding_model: str = "bge-m3",
        template_path: Optional[Path] = None,
    ) -> None:
        """
        Initialize controller with Ollama configuration.

        Args:
            ollama_host: Ollama server URL.
            llm_model: LLM model name.
            embedding_model: Embedding model name.
            template_path: Path to Excel template for detailed output.
        """
        self.ollama_host = ollama_host
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.template_path = template_path

    def execute(
        self,
        vsic_input: Path,
        mcc_input: Path,
        output: Path,
        output_detail: Path,
        top_k: int = 15,
        resume: bool = False,
        limit: Optional[int] = None,
    ) -> int:
        """
        Execute the mapping pipeline.

        Args:
            vsic_input: Path to VSIC JSON input.
            mcc_input: Path to MCC JSON input.
            output: Path to simple Excel output.
            output_detail: Path to detailed Excel output.
            top_k: Number of top-K candidates for LLM.
            resume: Whether to resume from checkpoint.
            limit: Maximum number of VSIC entries to process.

        Returns:
            Exit code (0 = success, 1 = file not found, 2 = Ollama error, 3 = IO error).
        """
        try:
            # Check input files
            if not vsic_input.exists():
                logger.error(f"VSIC input file not found: {vsic_input}")
                return 1
            if not mcc_input.exists():
                logger.error(f"MCC input file not found: {mcc_input}")
                return 1

            # Health check Ollama
            try:
                check_ollama_models(
                    self.ollama_host, self.llm_model, self.embedding_model
                )
            except RuntimeError as e:
                logger.error(f"Ollama health check failed: {e}")
                return 2

            # Load input data
            with open(vsic_input, "r", encoding="utf-8") as f:
                vsic_data = json.load(f)
                vsic_entries = vsic_data.get("vsic_list", [])

            with open(mcc_input, "r", encoding="utf-8") as f:
                mcc_data = json.load(f)
                mcc_entries = mcc_data.get("mcc_list", [])

            logger.info(
                f"Loaded {len(vsic_entries)} VSIC entries and "
                f"{len(mcc_entries)} MCC entries"
            )

            if limit is not None:
                vsic_entries = vsic_entries[:limit]
                logger.info(f"Limited processing to first {limit} entries")

            # Clamp top-k to reasonable range
            max_top_k = 100
            if top_k > max_top_k:
                logger.warning(
                    f"Requested --top-k {top_k} exceeds recommended "
                    f"maximum {max_top_k}. Clamping to avoid excessive "
                    "prompt size and timeout."
                )
                top_k = max_top_k

            # Initialize dependencies
            embedding_client = OllamaEmbeddingClient(
                self.ollama_host, self.embedding_model
            )
            llm_client = OllamaLLMClient(self.ollama_host, self.llm_model)

            checkpoint_path = output.parent / ".mapping-progress.json"
            checkpoint_repo = MappingCheckpointRepositoryImpl(checkpoint_path)

            valid_mcc_codes = [mcc["mcc"] for mcc in mcc_entries]
            validator = MccCodeValidator(valid_mcc_codes)

            use_case = MapVsicToMccUseCase(
                embedding_client=embedding_client,
                llm_client=llm_client,
                checkpoint_repo=checkpoint_repo,
                vsic_entries=vsic_entries,
                mcc_entries=mcc_entries,
                validator=validator,
            )

            simple_repo = SimpleMappingXlsxRepository()
            if self.template_path:
                detail_repo = DetailMappingXlsxRepository(self.template_path)
            else:
                logger.warning("No template path provided, skipping detailed output")
                detail_repo = None

            # Execute use case with progress bar
            entries = []
            with tqdm(total=len(vsic_entries), desc="Mapping VSIC to MCC") as pbar:
                for entry in use_case.execute(top_k=top_k, resume=resume):
                    entries.append(entry)
                    pbar.update(1)

            # Write outputs
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
