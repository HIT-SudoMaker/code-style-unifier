from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
import contextlib
from contextvars import ContextVar
from dataclasses import dataclass, fields, is_dataclass
import dis
import hashlib
import inspect
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

import torch

import chromatix_next.errors as _errors

from . import _execution_memory, _ownership
from ._tensors import _COMPLEX_DTYPE, _REAL_DTYPE
from .optics._assembly_facts import _FrozenAssembly
from .optics._meta_inference import _meta_inference
from .optics._role_contract import _component_contract_finding
from .optics.assembly import Assembly
from .optics.field import OpticalField
from .optics.intensity import Intensity
from .optics.polarization import PolarizationRepresentation
from .optics.ray_bundle import RayBundle

_PhysicalValue: TypeAlias = OpticalField | Intensity | RayBundle

_Calculation: TypeAlias = Callable[..., Mapping[str, _PhysicalValue]]

_InputFactory: TypeAlias = Callable[
    [torch.device],
    tuple[object, ...],
]

@dataclass(frozen=True, slots=True)
class _AssemblyReplayRequest:
    """
    承载冻结汇编的工作站重放请求

    """

    root: Assembly


@dataclass(frozen=True, slots=True)
class _CalculationReplayRequest:
    """
    承载托管计算的重放请求

    """

    calculation: _Calculation
    root: torch.nn.Module
    inputs: _InputFactory



    generator_stream_name: str | None



    invocation_signature: inspect.Signature


_ReplayRequest: TypeAlias = _AssemblyReplayRequest | _CalculationReplayRequest


@dataclass(frozen=True, slots=True)
class _PhysicalTensorContract:
    """
    承载执行边界对物理张量的精度与含义要求

    """

    tensor: torch.Tensor
    quantity_name: str
    expected_dtype: torch.dtype
    dtype_requirement: str


class NamedOutputs(Mapping[str, _PhysicalValue]):
    """
    成功运行产生的有序、只读物理值映射

    映射顺序由运行结果决定：Assembly ``expose`` 或模块级计算返回的 Mapping。
    值只包含 ``OpticalField``、``Intensity`` 或 ``RayBundle``。
    它不承担运行前注册、源锚或执行元数据；普通 Mapping 读取是唯一结果访问语义。

    """

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, _PhysicalValue]) -> None:
        del values
        raise _errors.AssemblyError(
            "named_outputs_run_only",
            "命名输出只由工作站运行成功后产生，不能自行构造；"
            "运行前请用 exposed_names 查看已声明的输出名",
        )

    @classmethod
    def _from_run(
        cls,
        ordered_pairs: tuple[tuple[str, _PhysicalValue], ...],
    ) -> NamedOutputs:

        instance = object.__new__(cls)
        ordered_values: dict[str, _PhysicalValue] = {}
        for name, value in ordered_pairs:
            if not isinstance(name, str) or not name:
                raise _errors.AssemblyError(
                    "named_outputs_name_invalid",
                    f"命名输出的名字必须是非空字符串，收到的是 {name!r}",
                )
            if name in ordered_values:
                raise _errors.AssemblyError(
                    f"named_outputs_name_duplicate:{name}",
                    f"命名输出里出现了两个 {name}，暴露名必须互不相同",
                )
            if not isinstance(value, (OpticalField, Intensity, RayBundle)):
                raise _errors.AssemblyError(
                    f"named_outputs_value_invalid:{name}",
                    f"命名输出 {name} 只能是光场、光强或光线束，"
                    f"收到的是 {type(value).__name__}",
                )
            ordered_values[name] = value
        instance._values = MappingProxyType(
            ordered_values
        )
        return instance

    def __getitem__(self, name: str) -> _PhysicalValue:
        return self._values[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


_ACTIVE_RUNTIME_MODULE_IDENTITIES: ContextVar[frozenset[int] | None] = (
    ContextVar(
        "_ACTIVE_RUNTIME_MODULE_IDENTITIES",
        default=None,
    )
)
_ACTIVE_REPLAY_VALUE_VALIDATOR: ContextVar[
    Callable[[object], None] | None
] = ContextVar(
    "_ACTIVE_REPLAY_VALUE_VALIDATOR",
    default=None,
)



_STREAM_DERIVATION_DESCRIPTION = (
    "sha256(f'{root_seed}|{stream_name}')[:8] -> 64-bit per-stream seed; "
    "torch.Generator(device=workstation.device).manual_seed(stream_seed)"
)


def _assert_root_seed(seed: int) -> int:



    if isinstance(seed, bool) or not isinstance(seed, int):
        raise _errors.WorkstationError(
            "workstation_random_root_seed_invalid",
            f"运行的根种子必须是整数，收到的是 {seed!r}",
        )
    return seed


def _derive_stream_seed(root_seed: int, stream_name: str) -> int:


    root_seed = _assert_root_seed(root_seed)
    if not isinstance(stream_name, str) or not stream_name:
        raise _errors.WorkstationError(
            "workstation_random_stream_name_invalid",
            f"派生随机流需要一个非空的流名，收到的是 {stream_name!r}",
        )
    digest = hashlib.sha256(
        f"{root_seed}|{stream_name}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass(frozen=True, slots=True)
class RunRecord:
    """
    一次 ``Workstation.run`` 旁的小而不可变的执行元数据记录（规约"Run Record"）

    仅记录描述该次运行所需的实现、设备、根 seed、PyTorch/CUDA 环境事实、
    峰值内存估计与执行边界。
    不载任何光数据、不参与计算、不是治理框架；一个 Example 可持久化它。
    产品固定双精度（ADR-0005），故不携带精度或装饰性数值格式字段。

    """

    device: str
    implementation: Literal["pytorch"]
    seed: int
    peak_memory_bytes: int
    memory_boundary_bytes: int
    torch_version: str
    is_cuda_available: bool
    cuda_device_name: str | None
    stream_derivation: str


def _expected_dtype(tensor: torch.Tensor) -> torch.dtype | None:


    if torch.is_complex(tensor):
        return _COMPLEX_DTYPE
    if torch.is_floating_point(tensor):
        return _REAL_DTYPE
    return None


def _schema_shape_of(value: _PhysicalValue) -> torch.Size:


    if isinstance(value, OpticalField):
        return value.envelope.shape
    if isinstance(value, RayBundle):
        return value.position.shape
    return value.values.shape


def _schema_dtype_of(value: _PhysicalValue) -> torch.dtype:

    if isinstance(value, OpticalField):
        return value.envelope.dtype
    if isinstance(value, RayBundle):
        return value.position.dtype
    return value.values.dtype





_RayPolarizationSchema = tuple[tuple[int, ...], torch.dtype] | None


def _ray_polarization_schema(
    value: _PhysicalValue,
) -> _RayPolarizationSchema:
    if isinstance(value, RayBundle):
        return (
            tuple(value.polarization_vector.shape),
            value.polarization_vector.dtype,
        )
    return None



_OutputSchemaEntry = tuple[
    str,
    type[object],
    tuple[int, ...],
    torch.dtype,
    PolarizationRepresentation | None,
    _RayPolarizationSchema,
]
_OutputSchema = tuple[_OutputSchemaEntry, ...]


class Workstation:
    """
    显式的本地计算持有者：设备、内存边界与托管/检查边界

    Args:
        arguments: 必须为空；工作站只能由明确的 CPU 或 CUDA 工厂创建
        keywords: 必须为空；设备与内存边界由工厂参数拥有

    Raises:
        WorkstationError: 调用时的状态或拓扑不满足该 Interface 契约

    """

    __slots__ = (
        "_device",
        "_memory_boundary_bytes",
        "__weakref__",
    )

    def __init__(
        self,
        *arguments: object,
        **keywords: object,
    ) -> None:
        del arguments, keywords
        raise _errors.WorkstationError(
            "workstation_factory_required",
            "工作站必须由显式工厂创建，请用 Workstation.cpu 或 Workstation.cuda；"
            "设备不做自动选择",
        )

    def __init_subclass__(cls, **keywords: object) -> None:
        del keywords
        raise _errors.WorkstationError(
            "workstation_subclass_unsupported",
            "工作站不支持派生子类，执行边界只有这一个实现",
        )

    @classmethod
    def cpu(cls) -> "Workstation":
        """
        显式选择 CPU 设备（无自动发现、无回退）

        Returns:
            CPU Workstation 上下文，用于无 CUDA 的执行与内存检查

        Raises:
            WorkstationError: 调用时的状态或拓扑不满足该 Interface 契约

        """
        if cls is not Workstation:
            raise _errors.WorkstationError(
                "workstation_subclass_unsupported",
                "工作站不支持派生子类，执行边界只有这一个实现",
            )
        device = torch.device("cpu")
        boundary = _execution_memory._default_memory_boundary_bytes(device)
        workstation = object.__new__(Workstation)
        object.__setattr__(workstation, "_device", device)
        object.__setattr__(workstation, "_memory_boundary_bytes", int(boundary))
        return workstation

    @classmethod
    def cuda(cls, device_index: int) -> "Workstation":
        """
        选择指定的 CUDA 设备

        Args:
            device_index: CUDA 运行时可见设备的零基整数索引

        Returns:
            CUDA Workstation 上下文，用于原生 CUDA 执行与内存检查

        Raises:
            WorkstationError: 调用时的状态或拓扑不满足该 Interface 契约

        """
        if not torch.cuda.is_available():
            raise _errors.WorkstationError(
                "workstation_cuda_unavailable",
                "这台机器上没有可用的 CUDA 设备，绝不自动回退到 CPU；"
                "要在 CPU 上运行请显式使用 Workstation.cpu",
            )
        device_count = torch.cuda.device_count()
        if (
            isinstance(device_index, bool)
            or not isinstance(device_index, int)
            or device_index < 0
            or device_index >= device_count
        ):
            raise _errors.WorkstationError(
                f"workstation_cuda_index_unavailable:{device_index}",
                f"这台机器有 {device_count} 张可用的 CUDA 卡，"
                f"编号从 0 开始，收到的编号是 {device_index!r}",
            )
        if cls is not Workstation:
            raise _errors.WorkstationError(
                "workstation_subclass_unsupported",
                "工作站不支持派生子类，执行边界只有这一个实现",
            )
        device = torch.device("cuda", device_index)

        def _construct() -> Workstation:


            boundary = _execution_memory._default_memory_boundary_bytes(device)
            built = object.__new__(Workstation)
            object.__setattr__(built, "_device", device)
            object.__setattr__(built, "_memory_boundary_bytes", int(boundary))
            return built

        return _ownership._claim_windows_cuda_singleton(_construct)

    @property
    def device(self) -> torch.device:
        """
        工作站目标设备，运行期不变

        Returns:
            返回当前设备对象，用于执行入口的设备身份查询

        """
        return self._device

    @property
    def memory_boundary_bytes(self) -> int:
        """
        显式设备内存边界（字节）；超出即 WorkstationError，不重试不回退

        Returns:
            返回当前 Workstation 的内存边界字节数

        """
        return self._memory_boundary_bytes

    def host(self, component: torch.nn.Module) -> torch.nn.Module:
        """
        显式把完整主体树（独立组件或冻结装配）的参数与缓冲移到目标设备

        规约"Workstation Host"：接受一个独立组件或一个**已冻结**装配；托管把其下全部
        Parameter 与 Buffer 搬到目标设备，**只移动设备、不改写浮点/复数 dtype**，
        不克隆主体、不改其光学含义。固定双精度（ADR-0005）要求整棵模块树的浮点量为
        float64、复数量为 complex128；任何 f32/c64 注册状态（整模块旧检查点或托管前被
        手动改写过的状态）都在移动前的预检即被拒绝。完整树由同一根独占；仅同工作站、
        同根的完整重复托管幂等，部分树或他站托管均在移动前拒绝。托管身份仅为运行时标记，
        永不入 ``state_dict``。``run`` 仅接受整棵模块树仍由同一工作站、同一装配根托管
        的冻结装配。

        Args:
            component: 要托管的模块树根，可以是独立光学组件或已冻结装配

        Returns:
            返回被托管的模块树根本身（即传入的 component）

        Raises:
            WorkstationError: 调用时的状态或拓扑不满足该 Interface 契约

        """
        if not isinstance(component, torch.nn.Module):
            raise _errors.WorkstationError(
                "workstation_host_subject_not_module",
                "托管的对象必须是一棵 PyTorch 模块树，"
                f"收到的是 {type(component).__name__}",
            )

        if isinstance(component, Assembly) and not component.is_frozen:
            raise _errors.WorkstationError(
                "workstation_host_assembly_not_frozen",
                "装配还没有冻结，请先调用 freeze 让拓扑与物理检查通过再托管",
            )
        if not isinstance(component, Assembly):
            finding = _component_contract_finding(component)
            if (
                finding is not None
                and not self._is_transparent_composition_root(component)
            ):
                raise _errors.WorkstationError(
                    finding,
                    "独立托管主体必须是一个合法光学元件，"
                    "或是不声明角色、且直接子模块全为合法元件的透明组合根",
                )

        self._assert_fixed_double_state(component)
        _ownership._commit_host(self, component, self._move_module_tree)
        return component

    @staticmethod
    def _is_transparent_composition_root(
        root: torch.nn.Module,
    ) -> bool:

        if any(
            "role" in ancestor.__dict__
            for ancestor in type(root).__mro__
        ):
            return False
        children = tuple(root.children())
        return bool(children) and all(
            _component_contract_finding(child) is None
            for child in children
        )

    def release(self, component: torch.nn.Module) -> torch.nn.Module:
        """
        解除本工作站对一棵完整主体树的所有权

        只有首次托管时的精确根可以解除所有权。即使树后来改变，首次根仍可清扫
        原 claim 中尚存活的模块。解除不移动 Parameter 或 Buffer；解除后的根可以
        由任一工作站重新托管。

        Args:
            component: 要解除托管的模块树根，须为首次托管时的精确根

        Returns:
            返回被解除托管的模块树根本身（即传入的 component）

        Raises:
            WorkstationError: 调用时的状态或拓扑不满足该 Interface 契约

        """
        if not isinstance(component, torch.nn.Module):
            raise _errors.WorkstationError(
                "workstation_release_subject_not_module",
                "解除托管的对象必须是一棵 PyTorch 模块树，"
                f"收到的是 {type(component).__name__}",
            )
        modules = tuple(component.modules())
        _ownership._release_root(self, component, modules)
        return component

    def run(
        self,
        calculation: Assembly | _Calculation,
        *,
        root: torch.nn.Module | None = None,
        inputs: _InputFactory | None = None,
        seed: int = 42,
    ) -> tuple[NamedOutputs, RunRecord]:
        """
        先以 meta 重放同一计算，再在可行时真实运行

        Args:
            calculation: 已冻结 Assembly 或受托管 Module 的执行根
            root: 接收状态的未托管模块树根
            inputs: 按调用签名或命名端口组织的设备本地输入
            seed: 用于派生可复现执行随机流的整数种子

        Returns:
            (NamedOutputs, RunRecord) 元组，分别为物理输出与不可变执行记录

        Raises:
            WorkstationError: 调用时的状态或拓扑不满足该 Interface 契约

        """

        seed = _assert_root_seed(seed)
        request = self._prepare_replay_request(
            calculation,
            root=root,
            inputs=inputs,
        )
        self._assert_hosted_root(request.root)
        if isinstance(request, _AssemblyReplayRequest):
            request.root.check()
        meta_peak, _meta_trace, meta_schema = self._measure_meta_replay(
            request,
            seed=seed,
        )
        self._assert_memory_feasible(meta_peak)
        (
            output_pairs,
            real_peak,
            _real_trace,
            real_schema,
        ) = self._measure_real_replay(
            request,
            seed=seed,
        )
        if real_peak > meta_peak:
            raise _errors.WorkstationError(
                "workstation_replay_memory_underestimated",
                "真实运行的 storage 生命周期峰值超过 meta 保守峰；"
                "计算的形状、别名或缓存行为不能由预检安全覆盖",
            )
        if real_schema != meta_schema:
            raise _errors.WorkstationError(
                "workstation_replay_output_schema_mismatch",
                "meta 预检与真实运行的输出名称、类型、形状或 dtype 不一致",
            )
        outputs = NamedOutputs._from_run(output_pairs)  # noqa: SLF001
        self._assert_output_placement(outputs)
        record = self._make_run_record(seed, meta_peak)
        return outputs, record

    def check(self, assembly: Any) -> None:
        """
        检查装配与 meta 内存可行性

        Args:
            assembly: 已由当前工作站托管并冻结的光学汇编

        Raises:
            WorkstationError: 调用时的状态或拓扑不满足该 Interface 契约

        """

        if not isinstance(assembly, Assembly):
            raise _errors.WorkstationError(
                "workstation_check_subject_not_assembly",
                "检查的对象必须是一个装配，"
                f"收到的是 {type(assembly).__name__}",
            )
        assembly.check()
        request = self._prepare_replay_request(
            assembly,
            root=None,
            inputs=None,
        )
        peak_bytes, _trace, _schema = self._measure_meta_replay(
            request,
            seed=42,
        )
        self._assert_memory_feasible(peak_bytes)

    def generator(
        self,
        stream_name: str,
        *,
        seed: int = 42,
    ) -> torch.Generator:
        """
        从根 seed 派生不改变全局随机状态的设备本地命名生成器

        Args:
            stream_name: 用于从执行种子派生独立随机流的稳定名称
            seed: 用于派生可复现执行随机流的整数种子

        Returns:
            返回由 stream_name 与 seed 派生的设备本地 torch.Generator

        """

        return self._generator_for_device(
            stream_name,
            seed=seed,
            device=self._device,
        )

    def _assert_memory_feasible(self, peak_bytes: int) -> None:
        if peak_bytes > self._memory_boundary_bytes:
            raise _errors.WorkstationError(
                "workstation_memory_check_infeasible",
                f"全路峰值需要 {peak_bytes} 字节，超过了本设备的内存边界 "
                f"{self._memory_boundary_bytes} 字节；请缩小网格或改用内存更大的设备",
            )

    def _prepare_replay_request(
        self,
        calculation: Assembly | _Calculation,
        *,
        root: torch.nn.Module | None,
        inputs: _InputFactory | None,
    ) -> _ReplayRequest:
        if isinstance(calculation, Assembly):
            if root is not None or inputs is not None:
                raise _errors.WorkstationError(
                    "workstation_run_assembly_arguments_forbidden",
                    "装配已经拥有冻结根与外部空间锚；"
                    "运行装配时不能再传 root 或 inputs",
                )
            return _AssemblyReplayRequest(calculation)
        self._assert_calculation(calculation)
        if not isinstance(root, torch.nn.Module):
            raise _errors.WorkstationError(
                "workstation_run_root_required",
                "普通计算必须显式传入已经托管的 PyTorch Module 根",
            )
        if not callable(inputs):
            raise _errors.WorkstationError(
                "workstation_run_inputs_required",
                "普通计算必须显式传入可重放的 inputs(device) 工厂",
            )
        invocation_signature = inspect.signature(calculation)
        variadic_parameter = next(
            (
                parameter
                for parameter in invocation_signature.parameters.values()
                if parameter.kind
                in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ),
            None,
        )
        if variadic_parameter is not None:
            raise _errors.WorkstationError(
                "workstation_calculation_invocation_incompatible",
                "直接 calculation 不能声明变长位置或关键字参数，"
                f"收到的是 {variadic_parameter.name!r}；"
                "请显式声明可重放调用接受的每个参数",
            )
        generator_stream_name = self._direct_generator_stream_name(
            calculation,
            invocation_signature,
        )
        return _CalculationReplayRequest(
            calculation=calculation,
            root=root,
            inputs=inputs,
            generator_stream_name=generator_stream_name,
            invocation_signature=invocation_signature,
        )

    @staticmethod
    def _assert_calculation(calculation: object) -> None:
        if (
            not inspect.isfunction(calculation)
            or calculation.__closure__ is not None
            or "<locals>" in calculation.__qualname__
        ):
            raise _errors.WorkstationError(
                "workstation_calculation_module_function_required",
                "普通计算必须是模块级函数，不能是 closure、绑定方法或 callable 对象；"
                "光学模块请通过显式 root 参数注入",
            )
        if any(
            instruction.opname in {"LOAD_ATTR", "LOAD_METHOD"}
            and instruction.argval == "forward"
            for instruction in dis.get_instructions(calculation)
        ):
            raise _errors.WorkstationError(
                "workstation_calculation_forward_call_forbidden",
                "普通计算必须通过 Module 调用语义执行元件，不能直接调用 forward；"
                "这样运行期模块边界和中间物理值校验才不会被绕过",
            )
        referenced_globals = (
            calculation.__globals__.get(name)
            for name in calculation.__code__.co_names
        )
        for value in referenced_globals:
            if isinstance(value, torch.nn.Module):
                raise _errors.WorkstationError(
                    "workstation_calculation_module_capture_forbidden",
                    "普通计算不能从全局捕获 PyTorch Module；"
                    "请只使用显式传入的 root",
                )
            if (
                inspect.isclass(value)
                and issubclass(value, torch.nn.Module)
            ):
                raise _errors.WorkstationError(
                    "workstation_calculation_runtime_module_forbidden",
                    "普通计算不能引用 PyTorch Module 类型来临时构造元件；"
                    "全部元件必须在托管 root 中预先注册",
                )

    @staticmethod
    def _direct_generator_stream_name(
        calculation: _Calculation,
        signature: inspect.Signature,
    ) -> str | None:



        parameters = signature.parameters
        if "generator" not in parameters:
            return None
        generator_parameter = parameters["generator"]
        if generator_parameter.kind is not inspect.Parameter.KEYWORD_ONLY:
            raise _errors.WorkstationError(
                "workstation_calculation_generator_must_be_keyword_only",
                "直接 calculation 的 generator 参数必须为 keyword-only，"
                f"收到的是 {generator_parameter.kind.name} 形参数",
            )
        return calculation.__name__

    @staticmethod
    def _assert_invocation_compatible(
        signature: inspect.Signature,
        arguments: tuple[object, ...],
        keywords: Mapping[str, object],
    ) -> None:


        try:
            signature.bind(*arguments, **keywords)
        except TypeError as error:
            raise _errors.WorkstationError(
                "workstation_calculation_invocation_incompatible",
                f"直接 calculation 的调用形状与 input 不兼容：{error}",
            ) from error

    def _assert_hosted_root(self, root: torch.nn.Module) -> None:
        hosted_modules = _ownership._assert_hosted(self, root)
        self._assert_module_tree_placement(hosted_modules)

    def _measure_meta_replay(
        self,
        request: _ReplayRequest,
        *,
        seed: int,
    ) -> tuple[
        int,
        tuple[int, ...],
        _OutputSchema,
    ]:
        modules = tuple(request.root.modules())
        owned_bytes = _execution_memory._owned_memory_bytes(modules)
        unfrozen_assembly_facts: _FrozenAssembly | None = None
        if (
            isinstance(request, _AssemblyReplayRequest)
            and not request.root.is_frozen
        ):
            unfrozen_assembly_facts = request.root._execution_facts()  # noqa: SLF001
        with _meta_inference(modules) as sandbox:
            meta_root = sandbox.module(request.root)
            if (
                unfrozen_assembly_facts is not None
                and isinstance(meta_root, Assembly)
            ):
                meta_root._assume_frozen_facts(  # noqa: SLF001
                    unfrozen_assembly_facts
                )
            with _execution_memory._trace_storage_lifetimes(
                excluded_tensors=sandbox._owned_tensors,
            ) as trace:
                values = self._invoke_replay(
                    request,
                    root=meta_root,
                    device=torch.device("meta"),
                    seed=seed,
                    observe_value=trace.observe_value,
                )
                trace.observe_value(values)
                output_pairs = self._validate_output_mapping(
                    values,
                    device=torch.device("meta"),
                )
        return (
            _execution_memory._conservative_peak_bytes(
                owned_bytes=owned_bytes,
                dynamic_bytes=trace.peak_bytes,
            ),
            trace.allocation_trace,
            self._output_schema(output_pairs),
        )

    def _measure_real_replay(
        self,
        request: _ReplayRequest,
        *,
        seed: int,
    ) -> tuple[
        tuple[tuple[str, _PhysicalValue], ...],
        int,
        tuple[int, ...],
        _OutputSchema,
    ]:
        modules = tuple(request.root.modules())
        owned_tensors = tuple(
            tensor
            for module in modules
            for tensor in (
                *module._parameters.values(),
                *module._buffers.values(),
            )
            if tensor is not None
        )
        owned_bytes = _execution_memory._owned_memory_bytes(modules)
        with _execution_memory._trace_storage_lifetimes(
            excluded_tensors=owned_tensors,
        ) as trace:
            values = self._invoke_replay(
                request,
                root=request.root,
                device=self._device,
                seed=seed,
                observe_value=trace.observe_value,
            )
            trace.observe_value(values)
            output_pairs = self._validate_output_mapping(
                values,
                device=self._device,
            )
        return (
            output_pairs,
            _execution_memory._conservative_peak_bytes(
                owned_bytes=owned_bytes,
                dynamic_bytes=trace.peak_bytes,
            ),
            trace.allocation_trace,
            self._output_schema(output_pairs),
        )

    @staticmethod
    def _output_schema(
        output_pairs: tuple[tuple[str, _PhysicalValue], ...],
    ) -> _OutputSchema:
        return tuple(
            (
                name,
                type(value),
                tuple(_schema_shape_of(value)),
                _schema_dtype_of(value),
                (
                    value.polarization_representation
                    if isinstance(value, OpticalField)
                    else None
                ),
                _ray_polarization_schema(value),
            )
            for name, value in output_pairs
        )

    def _invoke_replay(
        self,
        request: _ReplayRequest,
        *,
        root: torch.nn.Module,
        device: torch.device,
        seed: int,
        observe_value: Callable[[object], None],
    ) -> Mapping[str, _PhysicalValue]:
        with self._reject_runtime_modules(
            tuple(root.modules()),
            validate_value=lambda value: self._assert_physical_values_in(
                value,
                device=device,
            ),
        ):
            if isinstance(request, _AssemblyReplayRequest):
                assert isinstance(root, Assembly)
                return root._replay(  # noqa: SLF001
                    generator_for=lambda name: self._generator_for_device(
                        name,
                        seed=seed,
                        device=device,
                    ),
                    validate_value=lambda value: (
                        self._assert_physical_value(
                            value,
                            device=device,
                        )
                    ),
                )
            input_values = request.inputs(device)
            if not isinstance(input_values, tuple):
                raise _errors.WorkstationError(
                    "workstation_inputs_result_invalid",
                    "inputs(device) 必须返回参数元组",
                )
            observe_value(input_values)
            self._assert_physical_values_in(input_values, device=device)
            invocation_keywords: dict[str, object] = {}
            if request.generator_stream_name is not None:
                invocation_keywords["generator"] = self._generator_for_device(
                    request.generator_stream_name,
                    seed=seed,
                    device=device,
                )
            self._assert_invocation_compatible(
                request.invocation_signature,
                (root, *input_values),
                invocation_keywords,
            )
            return request.calculation(
                root,
                *input_values,
                **invocation_keywords,
            )

    @staticmethod
    @contextlib.contextmanager
    def _reject_runtime_modules(
        allowed_modules: tuple[torch.nn.Module, ...],
        *,
        validate_value: Callable[[object], None],
    ) -> Iterator[None]:
        allowed_identities = frozenset(id(module) for module in allowed_modules)
        module_token = _ACTIVE_RUNTIME_MODULE_IDENTITIES.set(
            allowed_identities
        )
        value_token = _ACTIVE_REPLAY_VALUE_VALIDATOR.set(validate_value)

        def _require_managed_module(
            module: torch.nn.Module,
            arguments: tuple[object, ...],
        ) -> None:
            active_identities = _ACTIVE_RUNTIME_MODULE_IDENTITIES.get()
            if (
                active_identities is not None
                and id(module) not in active_identities
            ):
                raise _errors.WorkstationError(
                    "workstation_calculation_runtime_module_forbidden",
                    "计算在运行期间调用了未纳入托管根的临时 Module；"
                    "请在 host 前把全部光学元件注册为 root 的子模块",
                )
            active_validator = _ACTIVE_REPLAY_VALUE_VALIDATOR.get()
            if active_validator is not None:
                active_validator(arguments)

        def _require_valid_result(
            module: torch.nn.Module,
            arguments: tuple[object, ...],
            result: object,
        ) -> None:
            del module, arguments
            active_validator = _ACTIVE_REPLAY_VALUE_VALIDATOR.get()
            if active_validator is not None:
                active_validator(result)

        pre_handle = torch.nn.modules.module.register_module_forward_pre_hook(
            _require_managed_module
        )
        post_handle = torch.nn.modules.module.register_module_forward_hook(
            _require_valid_result
        )
        try:
            yield
        finally:
            post_handle.remove()
            pre_handle.remove()
            _ACTIVE_REPLAY_VALUE_VALIDATOR.reset(value_token)
            _ACTIVE_RUNTIME_MODULE_IDENTITIES.reset(module_token)

    def _validate_output_mapping(
        self,
        values: object,
        *,
        device: torch.device,
    ) -> tuple[tuple[str, _PhysicalValue], ...]:
        if not isinstance(values, Mapping):
            raise _errors.WorkstationError(
                "workstation_calculation_outputs_invalid",
                "计算必须返回按科学读序排列的命名物理值 Mapping",
            )
        output_pairs: list[tuple[str, _PhysicalValue]] = []
        for name, value in values.items():
            if not isinstance(name, str) or not name:
                raise _errors.WorkstationError(
                    "workstation_calculation_output_name_invalid",
                    "每个计算输出都需要非空自然语言名字",
                )
            if not isinstance(value, (OpticalField, Intensity, RayBundle)):
                raise _errors.WorkstationError(
                    f"workstation_calculation_output_value_invalid:{name}",
                    f"输出 {name} 必须是 OpticalField、Intensity 或 RayBundle",
                )
            self._assert_physical_value(value, device=device)
            output_pairs.append((name, value))
        if not output_pairs:
            raise _errors.WorkstationError(
                "workstation_calculation_outputs_empty",
                "计算至少要返回一个命名物理值",
            )
        return tuple(output_pairs)

    def _assert_physical_values_in(
        self,
        value: object,
        *,
        device: torch.device,
    ) -> None:
        for physical_value in self._physical_values_in(value):
            self._assert_physical_value(physical_value, device=device)

    @classmethod
    def _physical_values_in(
        cls,
        value: object,
        *,
        visited: set[int] | None = None,
    ) -> Iterator[_PhysicalValue]:

        if isinstance(value, (OpticalField, Intensity, RayBundle)):
            yield value
            return
        if visited is None:
            visited = set()
        value_identity = id(value)
        if value_identity in visited:
            return
        if isinstance(value, (tuple, list)):
            visited.add(value_identity)
            for item in value:
                yield from cls._physical_values_in(item, visited=visited)
            return
        if isinstance(value, Mapping):
            visited.add(value_identity)
            for item in value.values():
                yield from cls._physical_values_in(item, visited=visited)
            return
        if is_dataclass(value) and not isinstance(value, type):
            visited.add(value_identity)
            for field in fields(value):
                yield from cls._physical_values_in(
                    getattr(value, field.name),
                    visited=visited,
                )


    def _physical_tensor_contracts(
        self,
        value: _PhysicalValue,
    ) -> Iterator[_PhysicalTensorContract]:
        if isinstance(value, RayBundle):
            yield from self._ray_bundle_tensor_contracts(value)
            return
        if isinstance(value, OpticalField):
            yield _PhysicalTensorContract(
                tensor=value.envelope,
                quantity_name="光场包络",
                expected_dtype=_COMPLEX_DTYPE,
                dtype_requirement=(
                    f"光场包络必须使用固定复精度 {_COMPLEX_DTYPE}"
                ),
            )
        else:
            yield _PhysicalTensorContract(
                tensor=value.values,
                quantity_name="光强",
                expected_dtype=_REAL_DTYPE,
                dtype_requirement=(
                    f"光强必须使用固定实精度 {_REAL_DTYPE}"
                ),
            )
        for grid_tensor in (
            *value.grid.sample_spacing,
            *value.grid.first_sample_position,
        ):
            yield _PhysicalTensorContract(
                tensor=grid_tensor,
                quantity_name="空间网格",
                expected_dtype=_REAL_DTYPE,
                dtype_requirement=(
                    f"空间网格必须使用固定实精度 {_REAL_DTYPE}"
                ),
            )
        if isinstance(value, OpticalField):
            for length in value.path_reference.lengths:
                if isinstance(length, torch.Tensor):
                    yield _PhysicalTensorContract(
                        tensor=length,
                        quantity_name="光程参考",
                        expected_dtype=torch.float64,
                        dtype_requirement=(
                            "光程参考必须使用设备本地 float64 光程累加精度"
                        ),
                    )

    def _ray_bundle_tensor_contracts(
        self,
        value: RayBundle,
    ) -> Iterator[_PhysicalTensorContract]:



        for tensor, quantity_name in (
            (value.position, "光线束位置"),
            (value.direction, "光线束方向"),
            (value.power, "光线束功率"),
            (value.refractive_index, "光线束折射率"),
        ):
            yield _PhysicalTensorContract(
                tensor=tensor,
                quantity_name=quantity_name,
                expected_dtype=_REAL_DTYPE,
                dtype_requirement=(
                    f"{quantity_name}必须使用固定实精度 {_REAL_DTYPE}"
                ),
            )
        yield _PhysicalTensorContract(
            tensor=value.polarization_vector,
            quantity_name="光线束偏振方向",
            expected_dtype=_COMPLEX_DTYPE,
            dtype_requirement=(
                f"光线束偏振方向必须使用固定复精度 {_COMPLEX_DTYPE}"
            ),
        )
        yield _PhysicalTensorContract(
            tensor=value.optical_path,
            quantity_name="光线束光程",
            expected_dtype=torch.float64,
            dtype_requirement=(
                "光线束光程必须使用设备本地 float64 光程累加精度"
            ),
        )
        yield _PhysicalTensorContract(
            tensor=value.status,
            quantity_name="光线束状态",
            expected_dtype=torch.uint8,
            dtype_requirement=(
                "光线束状态必须使用非浮点 bitmask dtype（uint8）"
            ),
        )

    def _assert_physical_value(
        self,
        value: _PhysicalValue,
        *,
        device: torch.device,
    ) -> None:
        contracts = tuple(
            self._physical_tensor_contracts(value)
        )
        if any(contract.tensor.device != device for contract in contracts):
            message = f"重放物理值必须位于 {device}，不能混入真实或其他设备张量"
            raise _errors.WorkstationError(
                "workstation_replay_physical_value_device_invalid",
                message,
            )
        for contract in contracts:
            if contract.tensor.dtype is contract.expected_dtype:
                continue
            raise _errors.WorkstationError(
                "workstation_run_physical_value_dtype_invalid",
                f"{contract.dtype_requirement}，"
                f"收到的是 {contract.tensor.dtype}",
            )

    def _assert_tensor_placement(self, tensor: torch.Tensor) -> None:
        if tensor.device != self._device:
            raise _errors.WorkstationError(
                "workstation_run_device_mismatch",
                f"本工作站绑定在 {self._device}，"
                f"却遇到了位于 {tensor.device} 的张量",
            )
        expected = _expected_dtype(tensor)
        if expected is not None and tensor.dtype is not expected:
            raise _errors.WorkstationError(
                "workstation_run_precision_mismatch",
                f"固定双精度要求 {expected}，"
                f"却遇到了 {tensor.dtype} 的张量；"
                "托管之后不要再自行改变模块的 dtype",
            )

    def __repr__(self) -> str:
        return f"<Workstation device={self._device!s}>"

    @staticmethod
    def _generator_for_device(
        stream_name: str,
        *,
        seed: int,
        device: torch.device,
    ) -> torch.Generator:
        generator_device = (
            torch.device("cpu")
            if device.type == "meta"
            else device
        )
        generator = torch.Generator(device=generator_device)
        generator.manual_seed(_derive_stream_seed(seed, stream_name))
        return generator

    def _make_run_record(self, seed: int, peak_memory_bytes: int) -> RunRecord:


        cuda_device_name: str | None = None
        if self._device.type == "cuda" and torch.cuda.is_available():
            index = self._device.index if self._device.index is not None else 0
            try:
                cuda_device_name = torch.cuda.get_device_name(index)
            except RuntimeError:
                cuda_device_name = None
        return RunRecord(
            device=str(self._device),
            implementation="pytorch",
            seed=seed,
            peak_memory_bytes=int(peak_memory_bytes),
            memory_boundary_bytes=int(self._memory_boundary_bytes),
            torch_version=str(torch.__version__),
            is_cuda_available=bool(torch.cuda.is_available()),
            cuda_device_name=cuda_device_name,
            stream_derivation=_STREAM_DERIVATION_DESCRIPTION,
        )

    def _move_module_tree(
        self,
        modules: tuple[torch.nn.Module, ...],
    ) -> None:





        staged_by_storage: dict[int, torch.Tensor] = {}
        parameter_rebinds: list[tuple[torch.nn.Parameter, torch.Tensor]] = []
        buffer_rebinds: list[tuple[torch.nn.Module, str, torch.Tensor]] = []
        for submodule in modules:
            for parameter in submodule._parameters.values():
                if parameter is None:
                    continue
                storage_identity = int(parameter.untyped_storage()._cdata)
                staged = staged_by_storage.get(storage_identity)
                if staged is None:
                    staged = parameter.detach().to(device=self._device)
                    staged_by_storage[storage_identity] = staged
                parameter_rebinds.append((parameter, staged))
            for name, buffer in submodule._buffers.items():
                if buffer is None:
                    continue
                storage_identity = int(buffer.untyped_storage()._cdata)
                staged = staged_by_storage.get(storage_identity)
                if staged is None:
                    staged = buffer.to(device=self._device)
                    staged_by_storage[storage_identity] = staged
                buffer_rebinds.append((submodule, name, staged))
        for parameter, staged in parameter_rebinds:
            parameter.data = staged
        for submodule, name, staged in buffer_rebinds:
            submodule._buffers[name] = staged

    def _assert_fixed_double_state(
        self,
        component: torch.nn.Module,
    ) -> None:



        checked_tensors: set[int] = set()
        for submodule in component.modules():
            for tensor in (
                *(
                    tensor
                    for tensor in submodule._parameters.values()
                    if tensor is not None
                ),
                *(
                    tensor
                    for tensor in submodule._buffers.values()
                    if tensor is not None
                ),
            ):
                tensor_identity = id(tensor)
                if tensor_identity in checked_tensors:
                    continue
                checked_tensors.add(tensor_identity)
                expected = _expected_dtype(tensor)
                if expected is None:
                    continue
                if tensor.dtype is not expected:
                    raise _errors.WorkstationError(
                        "workstation_host_dtype_invalid",
                        f"模块树含 {tensor.dtype} 的 {expected} 张量；"
                        "工作站固定双精度（ADR-0005），"
                        "实数量须 float64、复数量须 complex128，"
                        "请在托管前把模块状态恢复到固定双精度",
                    )

    def _assert_module_tree_placement(
        self,
        modules: tuple[torch.nn.Module, ...],
    ) -> None:
        for submodule in modules:
            for parameter in submodule._parameters.values():
                if parameter is not None:
                    self._assert_tensor_placement(parameter)
            for buffer in submodule._buffers.values():
                if buffer is not None:
                    self._assert_tensor_placement(buffer)

    def _assert_output_placement(self, outputs: NamedOutputs) -> None:
        for value in outputs.values():
            self._assert_physical_value_placement(value)

    def _assert_physical_value_placement(
        self,
        value: _PhysicalValue,
    ) -> None:
        for contract in self._physical_tensor_contracts(value):
            self._assert_physical_tensor(contract)

    def _assert_physical_tensor(
        self,
        contract: _PhysicalTensorContract,
    ) -> None:
        if contract.tensor.device != self._device:
            raise _errors.WorkstationError(
                "workstation_run_physical_value_device_invalid",
                f"{contract.quantity_name}必须位于工作站设备 {self._device}，"
                f"收到的是 {contract.tensor.device}",
            )
        if contract.tensor.dtype is not contract.expected_dtype:
            raise _errors.WorkstationError(
                "workstation_run_physical_value_dtype_invalid",
                f"{contract.dtype_requirement}，"
                f"收到的是 {contract.tensor.dtype}",
            )
