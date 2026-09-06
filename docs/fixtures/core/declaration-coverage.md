# 声明与参数覆盖边界

本清单连接主要 CST 入口、命名角色、文档义务和公共入口测试。按语言查找具体声明，再核对其处理边界和测试中的实际断言。

“支持”表示有明确的结构处理；“排除”表示该位置不属于相应规则的自选名称；“受阻”表示主体已观察，但身份或完整性无法证明。
列出的测试只支持其具体输入与断言，不表示全部 grammar 组合覆盖。“无独立文档”仍可属于外层 callable 的参数合同。

## 定位方式

实现统一见 [review.rs](../../../src/review.rs) 的 `DeclarationReview::collect_node`、`observe_callable` 和 `parameter_binding`，表内补充具体函数名。
算法与状态解释见[技术参考](../../technical.md#语言观察)；本页记录覆盖证据，不另行定义规则。

| 测试缩写 | 文件 |
|---|---|
| I | [identifier_subjects.rs](../../../tests/identifier/subjects.rs) |
| F | [identifier_forms.rs](../../../tests/identifier/forms.rs) |
| D | [documentation_regressions.rs](../../../tests/documentation/layout.rs) |
| C | [cpp_documentation_roles.rs](../../../tests/documentation/native_roles.rs) |

## Python

| CST 入口 | 命名与文档 | 处理边界 | 专项测试与证据界限 |
|---|---|---|---|
| `function_definition`, `class_definition` | Function、Type；均进入文档主体 | 支持；枚举成员装饰器另见下行。`collect_node`；`observe_callable` | I `python_observes_each_binding_declaration_once_and_excludes_uses`；D `public_and_internal_method_tiers_close_per_profile` |
| `assignment`, `augmented_assignment`、解包目标 | 普通局部 Value，模块 assignment 为 ModuleBinding；无独立文档 | 支持；只提取目标；`self/cls` 属性为 Value，其他属性和 subscript 结构排除。`push_python_binding_target` | I `python_observes_each_binding_declaration_once_and_excludes_uses` 有解包、self 属性及 other 属性反对照；未见 augmented/subscript 专项成对计数 |
| 注解 `TypeAlias`、`TypeVar` 等调用赋值 | Alias／Type；无独立文档 | 支持直接导入身份；遮蔽不授予特殊角色。`python_type_parameter_assignment`、`python_type_alias_assignment` | I `python_native_sources_keep_declaration_roles`；I `python_native_roles_require_direct_import_and_binding_evidence`，含直接来源及同名遮蔽反例 |
| `type_alias_statement`, `type_parameters` | Type（现代 type 别名与旧注解 Alias 区别保留）；参数 Type；无独立文档 | 支持；`push_python_type_alias`、`push_python_type_parameters` | I `python_observes_type_parameters_anonymous_parameters_import_aliases`；I `alias_declarations_cover_four_language_forms` |
| 枚举类 assignment／`decorated_definition` | 已证明成员 Constant，nonmember Value／Function；函数节点仍经文档观察 | 动态 descriptor、未知装饰器、无法解释的 `_ignore_` 归属受阻；`python_variant_member_decorator`、`python_variant_member_is_resolved` | I `python_native_declaration_roles_keep_canonical_names`；I `python_unresolved_variant_declarations_keep_identifier_coverage_incomplete`；I `python_native_sources_keep_declaration_roles` 和上述 incomplete 测试含未遮蔽／遮蔽／直接 member 别名 |
| 命名、默认、typed、splat 参数及 lambda 参数 | Value；命名 callable 的参数合同；lambda 无独立文档主体 | 支持稳定名；`/`、`*`、comment 结构排除；不识别的参数保留文档不完整。`push_python_parameter_identifiers`、`python_parameter_identifier`；`observe_parameter_names` | I `python_typed_splat_observes_stable_parameter_names`；I `python_observes_type_parameters_anonymous_parameters_import_aliases`；D `python_parameter_comments_keep_documentation_completeness` |
| 方法首参数与固定绑定／协议方法 | Value + ProfileFixed；固定名仍可计数，文档 receiver 按结构去除 | 支持已证明 self/cls、staticmethod 等结构；其他位置同名不豁免。`python_receiver_spelling`；`python_fixed_binding_owner` | I `self_spelling_is_profile_owned`；I `python_fixed_spellings_are_structural_only`；D `python_receiver_role_and_controlled_punctuation_are_enforced` |
| `aliased_import`／无别名 import | 显式 alias 为 Alias；无独立文档 | 支持 alias 字段；DeclarationReview 无普通 import 名称入口，不把依赖导入路径当自选 alias。| I 前述 import aliases 测试；`tests/dependency_contract.rs — complex_python_and_rust_imports_cannot_pass_as_clean` 属依赖族证据，不能代替无别名命名计数反例 |
| `for_statement`, `for_in_clause`, `named_expression`, `as_pattern_target` | Value；无独立文档 | 循环、推导式目标、海象及 with/except 目标有入口。| I 有普通 for、with、except；推导式及海象未定位到专项公共计数正反例，仅有分派证据 |
| `case_pattern` 及 class/dict/keyword/as 子模式 | Value；`_` 为 Discard；无独立文档 | 支持递归绑定；点号值引用、class 名与 keyword 名结构排除。`push_python_case_bindings` | I 有简单 capture；I `underscore_discard_and_ordinary_binding_are_distinct` 有 wildcard／普通 `_` 对照；复杂模式组合未见成对覆盖 |

## Rust

| CST 入口 | 命名与文档 | 处理边界 | 专项测试与证据界限 |
|---|---|---|---|
| function／signature／macro items | Function；函数有文档，宏由公开属性决定文档 | 支持直接 item；trait impl 方法记录外部 trait 表面身份，不解析导入别名。`rust_trait_surface`；`rust_public_documentation_item` | I `rust_observes_items_generics_lifetimes_fields_variants_and_bindings_once`；I `external_owner_spellings_exempt_only_through_typed_rows`；D `rust_exposure_subjects_keep_direct_documentation_owners` |
| struct／enum／trait／type／union／associated_type items | Type；公开类型等与 unsafe trait 按实现进入文档；associated_type 不自动等同公开类型文档入口 | 支持显式 item 名称，文档子集独立。`rust_public_documentation_item` | I `rust_observes_items_generics_lifetimes_fields_variants_and_bindings_once`；D `rust_public_types_fields_and_variants_are_direct_subjects`；未见 associated_type 独立文档正反矩阵 |
| const／static／mod items、fields、enum variants | Constant／ModuleNamespace／Value／Variant；直接公开项、公开字段与公开 enum 的变体有文档 | 支持；可见性与命名角色分开。`rust_public_documentation_item` | I `rust_observes_items_generics_lifetimes_fields_variants_and_bindings_once`；D 两项公开主体测试 |
| type／const／lifetime parameters | Type／Constant／Lifetime；无独立文档主体 | 支持各 name 字段；不把所有泛型当值参数。| I `rust_observes_items_generics_lifetimes_fields_variants_and_bindings_once`；F `module_namespace_tag_lifetime_and_label_forms_are_not_unchecked` |
| use_as／extern_crate alias、声明 label | Alias／ModuleNamespace／Label；公开 use 可另有文档义务 | alias 支持；break/continue 的 label 引用结构排除；无 alias 不从该入口造主体。| I 覆盖 use alias、label 及 break 引用；extern_crate alias 未见专项公共测试 |
| parameter／self_parameter | pattern 中 Value；文档仅稳定单名可完成 | Rust self_parameter 结构排除（不同于 Python self 计数）；解构可有命名主体但不是稳定单文档参数名。`push_rust_parameter_identifiers`；`parameter_is_fixed`、`observe_parameter_names` | I `rust_observes_items_generics_lifetimes_fields_variants_and_bindings_once` 有普通参数；D `native_parameter_comments_keep_documentation_facts`；D `rust_named_variadic_signature_cleans_with_safety_role`；解构参数的文档受阻未见专项成对断言 |
| let／let_condition／for／match_arm／closure patterns | Value；无独立文档 | 支持模式入口，match guard 只作引用；struct 类型路径等结构排除。`push_rust_binding_pattern` | I `rust_observes_items_generics_lifetimes_fields_variants_and_bindings_once` tuple let；I `rust_variant_patterns_are_references_not_binding_declarations`；I `rust_match_pattern_bindings_are_judged_but_guards_are_not`；let_condition／for／closure 未见各自成对计数 |
| `_`、`None`、Self、raw identifiers | Discard；已识别 None 为引用；Self 仅 Type 为 LanguageFixed；raw 保留本地形式 | 支持有限结构规则；不能据此宣称解析所有枚举常量身份。`push_named_declaration` | I `rust_variant_patterns_are_references_not_binding_declarations`；I `rust_pascal_binding_remains_variant_reference` 断言 Pascal let 绑定报错；I 固定名/丢弃正反；F `four_language_role_forms_accept_the_frozen_baseline` |

## C 与 C++

| CST 入口 | 命名与文档 | 处理边界 | 专项测试与证据界限 |
|---|---|---|---|
| C/C++ preproc_def／preproc_function_def | 宏 Constant、函数式宏参数 Value；宏本身为非 callable 文档主体 | 支持直接名称与参数；不展开宏结果。`native_family_documentation_capability_needed` | I `procedural_source_observes_all_direct_declaration_kinds`；I `cpp_observes_declared_names_but_excludes_fixed_callable_spellings_and_uses`；宏文档与展开不混为一谈 |
| C tags／C++ struct、union、enum、class | C 为 Tag，C++ 为 Type；有非 callable 文档义务 | 支持有名 specifier；无名不造命名主体，但文档身份可受阻。`documentation_subject_name` | I `procedural_source_observes_all_direct_declaration_kinds`、`cpp_observes_declared_names_but_excludes_fixed_callable_spellings_and_uses`；C `cpp_non_callable_subject_does_not_require_public_tier` 有命名／匿名对照（仅 C++） |
| C/C++ type_definition、enumerator | Typedef／Enumerator；枚举项有文档，typedef 不在该非 callable 入口 | 支持每个 typedef declarator；C `_t` 有本地形式。`push_native_family_field_declarators` | I `procedural_source_observes_all_direct_declaration_kinds`；I 四语言 alias；F 形式正反；多 typedef 列表组合无专项证据声明 |
| C label／C++ label | C Label；C++ 不产生该命名主体；无独立文档 | 明确语言 guard，不把 C++ 标签当已检查。| I `procedural_source_observes_all_direct_declaration_kinds` 的 C `J` 计入；I `cpp_observes_declared_names_but_excludes_fixed_callable_spellings_and_uses` 的 C++ `Z` 排除，测试有精确候选与计数 |
| C++ namespace／namespace_alias／alias_declaration | ModuleNamespace／ModuleNamespace／Type；无独立文档入口 | 支持嵌套 namespace 名和显式 alias。`push_cplusplus_namespace_names` | I `cpp_observes_declared_names_but_excludes_fixed_callable_spellings_and_uses`；F `module_namespace_tag_lifetime_and_label_forms_are_not_unchecked`；I `alias_declarations_cover_four_language_forms` |
| C/C++ declaration／field_declaration／function_definition 的逐 declarator | Function 或对象 Value/Constant；每个函数应独立为文档主体，字段另按非 callable 文档入口 | 支持命名逐 declarator；文档观察逐个函数 declarator，不能只由声明节点的第一个 declarator 决定义务。`push_native_family_value_declarations`；`observe_callable` | C `native_declarator_documentation_subjects` 覆盖：对象前／函数前／指针对象前／双函数／纯函数指针；I `native_declarator_type_forms_keep_object_roles` |
| C/C++ pointer／array／parenthesized／function declarator | 对象与函数按名称向外的派生层级判定；函数指针对象无 callable 文档 | 顶层 const 对象为 Constant，指向 const 的普通指针为 Value；reference 不借被引对象 const 获得 Constant。`native_family_function_declarator`；`native_family_declaration_is_constant` | I `native_declarator_type_forms_keep_object_roles` 有 const pointer 正反及函数指针；C `native_declarator_documentation_subjects` 纯函数指针文档零主体对照 |
| C/C++ named／optional／variadic parameter_declaration | Value；外层函数参数合同 | 稳定 declarator 名支持；注释排除。`parameter_binding`、`observe_parameter_names` | D `native_parameter_comments_keep_documentation_facts`；C `parameter_completeness_is_monotone_across_parameter_kinds` |
| C/C++ 无名参数、`void`、空括号、裸 `...` | 无命名主体；影响参数文档完整性 | 单 void 完整；C 空括号不完整、C++ 空括号完整；裸变参／无法取稳定名受阻。`observe_parameter_names` | D `variadic_native_signatures_remain_incomplete_not_guessed`；C 单调完整性；`tests/documentation/public_contract.rs — missing_carrier_and_unknown_signature_remain_independent` |
| C++ template 类型／非类型／template-template／包参数 | 类型 Type；直接非类型 Constant；函数模板参数进入独立文档字段 | 支持直接参数；缺稳定名受阻，abbreviated auto 未擅自完成。`cplusplus_template_parameters`、`cplusplus_template_parameter_name` | C `manifest_owned_function_template_covers_each_direct_parameter`；C `unnamed_direct_template_parameter_blocks_documentation_closure`；C `abbreviated_function_template_cannot_seal_without_stable_identity` |
| C++ for_range_loop／structured_binding_declarator | Value；已证明的按值 const 数组元素 Constant；无独立文档 | 普通和结构化目标有入口；Constant 证明限于同一 compound 中紧邻在前（允许注释）的 primitive_type/sized_type_specifier 多维数组声明、直接名称作为 range 右侧且无 range initializer；其他 const 按值结构化绑定 Identifier 受阻，引用按 Value 策略处理。见 `cplusplus_constant_binding_is_proven`。`push_native_family_value_declarations` | I `native_binding_forms_keep_identifier_subjects`；F `cpp_constant_binding_roles` 覆盖：const 按值／普通按值正反、reference 对照；另有跨 compound、遮蔽、range initializer、mutable 成员和 tuple 引用元素的受阻对照 |
| C++ lambda_capture_initializer、lambda 参数、条件声明 | 初始化捕获及参数 Value；lambda 无独立命名 callable 文档 | 支持 left 捕获和参数入口；普通捕获引用不新增自选名称。| I `cpp_observes_declared_names_but_excludes_fixed_callable_spellings_and_uses` 有初始化捕获和 lambda 参数；I `native_binding_forms_keep_identifier_subjects` 有 if/while declaration；普通捕获反例未见独立计数断言 |
| C++ constructor／destructor／operator 固定拼写 | 从自选命名主体排除；仍有 callable 文档及作用说明 | 固定拼写排除不能消除文档义务；归属歧义受阻。`cplusplus_fixed_callable_spelling`；`observe_callable` | I `cpp_observes_declared_names_but_excludes_fixed_callable_spellings_and_uses` 固定名计数；C `manifest_owned_free_operator_requires_nonempty_effect_last`；C `manifest_owned_constructor_and_destructor_require_effect`；C `genuine_overload_ambiguity_stays_conservative` |

枚举装饰器身份、方法 receiver 和 property 文档归属分别验证。
I 的 `python_native_declaration_roles_keep_canonical_names` 与 D 的 `python_property_accessors_share_only_proven_direct_owner` 包含普通访问器及自定义装饰器的对照；解释边界见技术参考。

## 尚缺专项证据的边界

1. Python 推导式／海象、复杂 match 模式及 Rust let_condition／for／closure／extern_crate alias 有实现入口，本清单未定位到各自公共入口的成对计数／引用排除测试；邻近测试不能替代这些分支的证据。
2. 文档证据不对称：C++ 匿名类型有受阻对照；C 同类、Rust 解构参数文档受阻及 associated_type 文档边界未形成逐类正反矩阵。未定位到专项证据不自动构成实现缺陷。
3. 现有 declarator 顺序、数组范围 const 和装饰器遮蔽测试仅覆盖列举的局部组合。任意 tuple 协议、mutable 成员、动态赋值别名与宏展开不因这些测试而成为已证明支持的语义域；const 结构化绑定的未证明主体按上述边界受阻。
