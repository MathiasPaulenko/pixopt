# API Reference

## Core optimization

::: pixopt.optimizer.optimize_image

::: pixopt.optimizer.batch_optimize

::: pixopt.optimizer.optimize_directory

::: pixopt.optimizer.validate_optimize_params

::: pixopt.optimizer.change_extension

::: pixopt.optimizer.convert_to_favicon

## Models

::: pixopt.models.OptimizationResult

::: pixopt.models.BatchReport

::: pixopt.models.ImageInfo

::: pixopt.models.OutputFormat

::: pixopt.models.Anchor

::: pixopt.models.FitMode

## Progress

::: pixopt.progress.ProgressInfo

::: pixopt.progress.ProgressCallback

## Presets

::: pixopt.presets.BUILTIN_PRESETS

::: pixopt.presets.apply_preset

::: pixopt.presets.resolve_preset

::: pixopt.presets.load_custom_presets

::: pixopt.presets.get_preset_names

## EXIF

::: pixopt.exif.EXIFGroup

::: pixopt.exif.filter_exif

::: pixopt.exif.apply_filtered_exif

::: pixopt.exif.get_exif_groups

## Exceptions

::: pixopt.exceptions.PixoptError

::: pixopt.exceptions.ImageNotFoundError

::: pixopt.exceptions.OptimizationError

::: pixopt.exceptions.ConversionError

::: pixopt.exceptions.InvalidParameterError

::: pixopt.exceptions.UnsupportedFormatError

## Palette

::: pixopt.palette.extract_palette

::: pixopt.palette.PaletteResult

::: pixopt.palette.ColorSwatch

## Benchmark

::: pixopt.benchmark.benchmark_formats

::: pixopt.benchmark.BenchmarkResult

::: pixopt.benchmark.BenchmarkVariant

## Placeholders

::: pixopt.placeholder.generate_placeholder

::: pixopt.placeholder.extract_dominant_color

::: pixopt.placeholder.generate_lqip_datauri

::: pixopt.placeholder.generate_blurhash

## Smart format detection

::: pixopt.smart_format.detect_optimal_format

::: pixopt.smart_format.has_transparency

::: pixopt.smart_format.count_unique_colors

::: pixopt.smart_format.is_photo

## Srcset generation

::: pixopt.srcset_generator.generate_srcset_images

::: pixopt.srcset_generator.SrcsetImage

## Adaptive quality

::: pixopt.adaptive_quality.find_quality_for_target_size

## Visual comparison

::: pixopt.html_comparison.generate_comparison_html

## Watermark

::: pixopt.watermark.add_text_watermark

::: pixopt.watermark.add_image_watermark

::: pixopt.watermark.WatermarkPosition

::: pixopt.watermark.WatermarkResult

## Sprite

::: pixopt.sprite.create_sprite

::: pixopt.sprite.create_contact_sheet

::: pixopt.sprite.SpriteLayout

::: pixopt.sprite.SpriteResult

::: pixopt.sprite.SpriteSlot

## Bundle

::: pixopt.bundle.generate_asset_bundle

::: pixopt.bundle.BundleOptions

::: pixopt.bundle.AssetBundle

## In-memory I/O

::: pixopt.io_bytes.optimize_bytes

::: pixopt.io_bytes.optimize_base64

::: pixopt.io_bytes.bytes_to_image

::: pixopt.io_bytes.image_to_bytes

::: pixopt.io_bytes.base64_to_image

::: pixopt.io_bytes.image_to_base64

::: pixopt.io_bytes.BytesResult

::: pixopt.io_bytes.Base64Result

## PDF

::: pixopt.pdf_io.images_to_pdf

::: pixopt.pdf_io.pdf_to_images

::: pixopt.pdf_io.PdfExportResult

::: pixopt.pdf_io.PdfImportResult

::: pixopt.pdf_io.PdfPageInfo

## Perceptual hashing

::: pixopt.perceptual.compute_hash

::: pixopt.perceptual.phash

::: pixopt.perceptual.ahash

::: pixopt.perceptual.dhash

::: pixopt.perceptual.find_duplicates

::: pixopt.perceptual.scan_duplicates

::: pixopt.perceptual.hamming_distance

::: pixopt.perceptual.HashResult

::: pixopt.perceptual.DuplicateGroup

::: pixopt.perceptual.DuplicateReport

## Async API

::: pixopt.async_api.async_optimize_image

::: pixopt.async_api.async_batch_optimize

::: pixopt.async_api.async_optimize_bytes

::: pixopt.async_api.async_optimize_base64

::: pixopt.async_api.async_inspect_image

::: pixopt.async_api.async_scan_directory

::: pixopt.async_api.async_scan_duplicates

## Pipeline

::: pixopt.pipeline.Pipeline

::: pixopt.pipeline.PipelineResult

## Image inspection

::: pixopt.inspect.inspect_image

::: pixopt.inventory.scan_directory

::: pixopt.inventory.ScanEntry

::: pixopt.inventory.ScanReport

## Next-generation formats

::: pixopt.nextgen.NextGenFormat

::: pixopt.nextgen.detect_format_support

::: pixopt.nextgen.is_format_supported

::: pixopt.nextgen.convert_to_nextgen

::: pixopt.nextgen.ConversionResult

::: pixopt.nextgen.FormatSupport

::: pixopt.nextgen.FormatSupportInfo

## Quality metrics

::: pixopt.quality.compare_images

::: pixopt.quality.compute_ssim

::: pixopt.quality.compute_psnr

::: pixopt.quality.compute_mse

::: pixopt.quality.QualityMetrics
