from __future__ import annotations

from pathlib import Path

from data.data_source.dataset_root import resolve_dataset_root
from data.data_source.datasets.source_dataset import RawVisionDataset, SourceImageDataset
from data.data_source.indexing.idx_reader import RawIDXVisionDataset

FASHION_MNIST_PROVENANCE_URL = "https://github.com/zalandoresearch/fashion-mnist"
FASHION_MNIST_LICENSE_NAME = "MIT"


class BaseFashionMNISTDataset(SourceImageDataset):
    """
    仅使用显式准备好的本地IDX文件构造FashionMNIST数据源
    """

    CLASS_NAMES = [
        "T-shirt/top",
        "Trouser",
        "Pullover",
        "Dress",
        "Coat",
        "Sandal",
        "Shirt",
        "Sneaker",
        "Bag",
        "Ankle boot",
    ]
    _DEFAULT_ARRAY_RESOLUTION = (128, 128)
    _DEFAULT_IMAGE_RESOLUTION = (64, 64)

    def __init__(
        self,
        dataset_root: str | None = None,
        is_train: bool = True,
        array_resolution: tuple[int, int] = _DEFAULT_ARRAY_RESOLUTION,
        image_resolution: tuple[int, int] = _DEFAULT_IMAGE_RESOLUTION,
        samples_per_class: int | None = None,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> None:
        """
        FashionMNIST数据源

        Args:
            max_samples:       最大总采样数，None表示保留全部样本
            dataset_root:      数据集根目录，None时使用项目默认路径
            is_train:          是否加载训练集划分
            array_resolution:  数据源阶段占位参数，必须保持默认值
            image_resolution:  数据源阶段占位参数，必须保持默认值
            samples_per_class: 每类分层采样数量，None表示不采样
            random_seed:       分层采样随机种子

        Raises:
            ValueError:          当数据源阶段尺寸占位参数被修改时抛出
            FileNotFoundError:   当本地IDX原始文件缺失时抛出
        """
        if (
            array_resolution != self._DEFAULT_ARRAY_RESOLUTION
            or image_resolution != self._DEFAULT_IMAGE_RESOLUTION
        ):
            raise ValueError(
                "array_resolution和image_resolution属于后续管线阶段; "
                "data_source构造时应保持原始分辨率默认值"
            )

        resolved_dataset_root = resolve_dataset_root(dataset_root)
        raw_dataset = self._load_raw_dataset(
            dataset_root=resolved_dataset_root,
            is_train=is_train,
        )
        split_name = "train" if is_train else "test"
        super().__init__(
            raw_dataset=raw_dataset,
            class_names=self.CLASS_NAMES,
            dataset_name="fashion_mnist",
            split_name=split_name,
            samples_per_class=samples_per_class,
            max_samples=max_samples,
            random_seed=random_seed,
            provenance_url=FASHION_MNIST_PROVENANCE_URL,
            license_name=FASHION_MNIST_LICENSE_NAME,
            source_metadata={
                "source_format": "idx",
            },
        )

    def _load_raw_dataset(self, dataset_root: str, is_train: bool) -> RawVisionDataset:
        raw_root = Path(dataset_root) / "fashion_mnist" / "raw"
        if raw_root.exists():
            return RawIDXVisionDataset(
                root=dataset_root,
                dataset_dir="fashion_mnist",
                is_train=is_train,
            )

        raise FileNotFoundError(
            f"FashionMNIST local raw files are required at {raw_root}; "
            "prepare the dataset explicitly before constructing BaseFashionMNISTDataset."
        )
