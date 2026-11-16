# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unified parser configuration management for OpenViking.

This module consolidates all parser configuration classes that were previously
scattered across different modules. All configurations inherit from ParserConfig
and can be loaded from ov.conf files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParserConfig:
    """
    Base configuration class for all parsers.

    This serves as a foundation for parser-specific configurations,
    providing common fields and utilities for all parsers.

    Attributes:
        enabled: Whether the parser is enabled
        max_content_length: Maximum content length to process (characters)
        encoding: Default file encoding
        max_section_size: Legacy option, ignored by native Markdown splitting
        section_size_flexibility: Allow overflow to maintain coherence (0.0-1.0)
        max_section_chars: Target character limit per section. A single oversized
            Markdown table row may remain intact to preserve table semantics.
    """

    enabled: bool = True
    max_content_length: int = 100000
    encoding: str = "utf-8"

    # Smart splitting configuration
    max_section_size: int = 2048  # Legacy compatibility; splitting uses max_section_chars
    section_size_flexibility: float = 0.3  # Allow 30% overflow to maintain coherence
    max_section_chars: int = 2000  # Target character limit per section

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParserConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            ParserConfig instance

        Examples:
            >>> config = ParserConfig.from_dict({"max_content_length": 50000})
        """
        return cls(**{key: value for key, value in data.items() if key in cls.__dataclass_fields__})

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "ParserConfig":
        """
        Load configuration from YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            ParserConfig instance

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML is invalid

        Examples:
            >>> config = ParserConfig.from_yaml("config.yaml")
        """
        import yaml

        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.max_content_length <= 0:
            raise ValueError("max_content_length must be positive")

        if not self.encoding:
            raise ValueError("encoding cannot be empty")

        if self.max_section_size <= 0:
            raise ValueError("max_section_size must be positive")

        if not 0.0 <= self.section_size_flexibility <= 1.0:
            raise ValueError("section_size_flexibility must be between 0.0 and 1.0")

        if self.max_section_chars <= 0:
            raise ValueError("max_section_chars must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration as dictionary.

        Returns:
            Configuration dictionary

        Examples:
            >>> config = ParserConfig()
            >>> data = config.to_dict()
        """
        from dataclasses import asdict

        return asdict(self)


@dataclass
class PDFConfig(ParserConfig):
    """
    Configuration for PDF parsing.

    Supports three strategies:
    - "local": Use pdfplumber for local PDF→Markdown conversion
    - "mineru": Use MinerU API for remote PDF→Markdown conversion
    - "auto": Try local first, fallback to MinerU if available

    Attributes:
        strategy: Parsing strategy ("local" | "mineru" | "auto")
        mineru_endpoint: MinerU API endpoint URL
        mineru_timeout: MinerU request timeout in seconds
        mineru_bodys: Additional MinerU API multipart form fields
    """

    strategy: str = "auto"  # "local" | "mineru" | "auto"

    # MinerU API configuration
    mineru_endpoint: Optional[str] = None  # API endpoint URL
    mineru_timeout: float = 300.0  # Request timeout in seconds (5 minutes)
    mineru_bodys: Optional[dict] = None  # Additional API multipart form fields

    # Heading detection configuration
    heading_detection: str = "auto"  # "bookmarks" | "font" | "auto" | "none"
    font_heading_min_delta: float = 1.5  # Minimum font size delta from body text (pt)
    max_heading_levels: int = 4  # Maximum heading levels for font analysis

    # Image extraction configuration
    image_resolution: int = 300  # Rendering DPI for extracted image regions

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate base class fields
        super().validate()

        # Validate PDF-specific fields
        if self.strategy not in ("local", "mineru", "auto"):
            raise ValueError(
                f"Invalid strategy '{self.strategy}'. Must be 'local', 'mineru', or 'auto'"
            )

        if self.strategy == "mineru":
            if not self.mineru_endpoint:
                raise ValueError("mineru_endpoint is required when strategy='mineru'")

        if self.mineru_timeout <= 0:
            raise ValueError("mineru_timeout must be positive")

        if self.heading_detection not in ("bookmarks", "font", "auto", "none"):
            raise ValueError(f"Invalid heading_detection: {self.heading_detection}")

        if self.font_heading_min_delta <= 0:
            raise ValueError("font_heading_min_delta must be positive")


@dataclass
class CodeHostingConfig(ParserConfig):
    """
    Base configuration for code hosting platform domains.

    Attributes:
        code_hosting_domains: List of allowed generic code hosting domains
        github_domains: List of GitHub domains (github.com, www.github.com)
        gitlab_domains: List of GitLab domains (gitlab.com, www.gitlab.com)
        azure_devops_domains: List of Azure DevOps domains (dev.azure.com, ssh.dev.azure.com)
    """

    # Code hosting platform configuration
    code_hosting_domains: list = None
    github_domains: list = None
    gitlab_domains: list = None
    azure_devops_domains: list = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.code_hosting_domains is None:
            self.code_hosting_domains = [
                "github.com",
                "gitlab.com",
                "gitcode.com",
                "gitee.com",
                "bitbucket.org",
                "codeberg.org",
                "gitea.com",
                "atomgit.com",
                "git.sr.ht",
            ]
        if self.github_domains is None:
            self.github_domains = ["github.com", "www.github.com"]
        if self.gitlab_domains is None:
            self.gitlab_domains = ["gitlab.com", "www.gitlab.com"]
        if self.azure_devops_domains is None:
            self.azure_devops_domains = [
                "dev.azure.com",
                "ssh.dev.azure.com",
                "vs-ssh.visualstudio.com",
            ]


@dataclass
class CodeConfig(CodeHostingConfig):
    """
    Configuration for code parsing.

    Attributes:
        extract_functions: Legacy compatibility field; ignored by the fixed skeleton route
        extract_classes: Legacy compatibility field; ignored by the fixed skeleton route
        extract_imports: Legacy compatibility field; ignored by the fixed skeleton route
        include_comments: Legacy compatibility field; ignored by the fixed skeleton route
        max_line_length: Legacy compatibility field; ignored by the fixed skeleton route
        language_hint: Legacy compatibility field; ignored by the fixed skeleton route
        max_token_limit: Legacy compatibility field; ignored by the fixed skeleton route
        truncation_strategy: Legacy compatibility field; ignored by the fixed skeleton route
        warn_on_truncation: Legacy compatibility field; ignored by the fixed skeleton route
        github_raw_domain: Domain for GitHub raw content (raw.githubusercontent.com)
    """

    extract_functions: bool = True
    extract_classes: bool = True
    extract_imports: bool = True
    include_comments: bool = True
    max_line_length: int = 1000
    language_hint: Optional[str] = None
    max_token_limit: int = 50000  # Maximum tokens to process per file
    truncation_strategy: str = "head"  # "head", "tail", or "balanced"
    warn_on_truncation: bool = True
    github_raw_domain: str = "raw.githubusercontent.com"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeConfig":
        """Create code configuration, accepting removed fields for upgrade compatibility."""

        data = dict(data)
        if "code_summary_mode" in data:
            data.pop("code_summary_mode", None)
            logger.warning(
                "code.code_summary_mode is deprecated and ignored; "
                "code summaries now always use the fixed skeleton route with LLM fallback"
            )

        return super().from_dict(data)

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate base class fields
        super().validate()

        # Validate code-specific fields
        if self.max_line_length <= 0:
            raise ValueError("max_line_length must be positive")

        if self.max_token_limit <= 0:
            raise ValueError("max_token_limit must be positive")

        if self.truncation_strategy not in ("head", "tail", "balanced"):
            raise ValueError(
                f"Invalid truncation_strategy '{self.truncation_strategy}'. "
                "Must be 'head', 'tail', or 'balanced'"
            )


@dataclass
class ImageConfig(ParserConfig):
    """
    Configuration for image parsing.

    Attributes:
        enable_ocr: Whether to perform OCR text extraction, not implemented
        enable_vlm: Whether to use VLM for visual understanding
        ocr_lang: Language for OCR (e.g., "chi_sim", "eng")
        vlm_model: VLM model to use (e.g., "gpt-4-vision")
        preview_max_dimension: Maximum dimension for preview resizing (resize if larger)
        max_file_size_mb: Maximum file size before triggering large image processing
        max_tile_dimension_px: Maximum dimension for individual tiles
        tile_overlap_px: Number of pixels to overlap between tiles
        large_image_threshold_dimension: Dimension threshold for large image detection
    """

    enable_ocr: bool = False
    enable_vlm: bool = True
    ocr_lang: str = "eng"
    vlm_model: Optional[str] = None
    preview_max_dimension: int = 2048
    # Large image processing settings
    max_file_size_mb: float = 10.0  # 10 MB
    max_tile_dimension_px: int = 2048  # 2048 pixels
    tile_overlap_px: int = 2  # 2 pixels
    large_image_threshold_dimension: int = 4096  # 4096 pixels

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate base class fields
        super().validate()

        # Validate image-specific fields
        if self.preview_max_dimension <= 0:
            raise ValueError("preview_max_dimension must be positive")
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if self.max_tile_dimension_px <= 0:
            raise ValueError("max_tile_dimension_px must be positive")
        if self.tile_overlap_px < 0:
            raise ValueError("tile_overlap_px must be non-negative")
        if self.large_image_threshold_dimension <= 0:
            raise ValueError("large_image_threshold_dimension must be positive")


@dataclass
class AudioConfig(ParserConfig):
    """
    Configuration for audio parsing.

    Attributes:
        enable_transcription: Whether to transcribe speech to text
        transcription_model: Model to use (e.g., "whisper-large-v3")
        language: Audio language (None for auto-detection)
        extract_metadata: Whether to extract audio metadata
    """

    enable_transcription: bool = True
    transcription_model: str = "whisper-large-v3"
    language: Optional[str] = None
    extract_metadata: bool = True

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate base class fields
        super().validate()

        # Validate audio-specific fields
        if not self.transcription_model:
            raise ValueError("transcription_model cannot be empty")


@dataclass
class VideoConfig(ParserConfig):
    """
    Configuration for video parsing.

    Attributes:
        extract_frames: Whether to extract key frames
        frame_interval: Seconds between frame extraction
        enable_transcription: Whether to transcribe audio track
        enable_vlm_description: Whether to use VLM for scene description
        max_duration: Maximum video duration to process (seconds)
    """

    extract_frames: bool = True
    frame_interval: float = 10.0
    enable_transcription: bool = True
    enable_vlm_description: bool = False
    max_duration: float = 3600.0  # 1 hour

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate base class fields
        super().validate()

        # Validate video-specific fields
        if self.frame_interval <= 0:
            raise ValueError("frame_interval must be positive")

        if self.max_duration <= 0:
            raise ValueError("max_duration must be positive")


@dataclass
class MarkdownConfig(ParserConfig):
    """
    Configuration for Markdown parsing.

    Attributes:
        preserve_links: Whether to preserve hyperlinks in output
        extract_frontmatter: Whether to REMOVE YAML frontmatter from the stored
            document body. Frontmatter is parsed into the parse result metadata
            regardless. Off by default: the parsed metadata is never persisted, so
            removing the block would silently lose those fields.
        include_metadata: Whether to include file metadata
        max_heading_depth: Maximum heading depth to include in structure
    """

    preserve_links: bool = True
    extract_frontmatter: bool = False
    include_metadata: bool = True
    max_heading_depth: int = 3

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate base class fields
        super().validate()

        # Validate markdown-specific fields
        if self.max_heading_depth < 1:
            raise ValueError("max_heading_depth must be at least 1")




from .parser_config_extra import (  # noqa: E402
    PARSER_CONFIG_REGISTRY,
    AnydocConfig,
    DirectoryConfig,
    FeishuConfig,
    HTMLConfig,
    SemanticConfig,
    TextConfig,
    WebFeedConfig,
    get_parser_config,
    load_parser_configs_from_dict,
)
