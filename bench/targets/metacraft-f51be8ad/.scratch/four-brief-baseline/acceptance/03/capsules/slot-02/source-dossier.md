# Case-neutral metalens consultation dossier

This dossier contains general decision principles, not a benchmark answer.
It deliberately contains no published period or height for any tested device.

1. The request's sampling ceiling is a hard legality bound, not an instruction
   to choose its largest candidate. A usable lattice also balances spatial
   sampling, unwanted diffraction risk, feature room, and simulation cost.
   Locator: https://optics.ansys.com/hc/en-us/articles/35797097445779-Introduction-to-metalens-workflows
2. A period above the request's order ceiling may retain additional propagating
   orders. Treat that as a visible risk rather than silently calling the
   response zeroth-order; prefer a lower-risk legal candidate unless the local
   phase-control grounds justify accepting the warning.
   Locator: doi:10.1186/s43593-025-00111-y
3. For propagation phase, optical path accumulation scales approximately with
   effective-index contrast times height. Use this only as a conservative
   dimensional screen for 2-pi reach; a periodic response sweep must later
   prove phase coverage and transmission.
   Locator: https://optics.ansys.com/hc/en-us/articles/360042097313-Metalens
4. For geometric phase, rotation supplies phase only when the element provides
   suitable polarization conversion. Use the request's retardance forecast as
   a ranking ground, not as completed Jones-matrix evidence.
   Locator: doi:10.1126/science.1252727
5. Respect the emitted fabrication interval, height grid, aspect limit, and
   candidate identities exactly. Prefer an interior conservative choice when
   neighboring candidates are comparably supported, and stop at WaitingStudies
   because neither this dossier nor scalar material indices prove a cell.
