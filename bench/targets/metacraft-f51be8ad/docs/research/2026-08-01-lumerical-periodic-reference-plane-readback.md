# Lumerical periodic reference-plane read-back

Date: 2026-08-01

> 2026-08-05 mechanism correction: the installed product rejected
> `setnamed` mutation of the constructed internal `T` child after group setup.
> The external position and sampling observations below remain unchanged.
> MetaCraft's deterministic repair candidate carries `specified position` in
> a marked parent-group setup contract, then runs setup and strictly reads the
> constructed child back. Installed-version acceptance remains unproved until
> a separately authorized Native gate runs at a new application root.

## Question

Why did the fresh Ticket 09 qualification declare the internal transmission
plane at 800 nm but observe the sampled reference surface at
804.347826086957 nm?

## Product evidence

The retained failed project lives under the ticket-specific external canary
root at:

`runs/qualification/lumerical-qualification-20260801T041348588149Z/transmission/after.fsp`

Its grating response reads back:

- group center: 250 nm;
- internal `T` object position: 550 nm in the relative group frame;
- declared world transmission plane: 800 nm;
- `T` monitor spatial interpolation: `nearest mesh cell`;
- sampled dataset z coordinate: 804.347826086957 nm.

A separate native coordinate probe aligned the monitor with the mesh. In that
case the same 550 nm relative child position was returned by the dataset as an
800 nm world coordinate. The dataset therefore does not require a second
group-center addition. Doing so would double-convert the coordinate.

The Lumerical frequency-domain monitor documentation states that monitors use
the nearest mesh cell by default and that `specified position` records the
field at the requested monitor position. The grating response owns its
internal source, reflection monitor, and transmission monitor. Official group
and scripting documentation supports the parent setup-script seam used by
MetaCraft's repair candidate; it does not prove that the installed
`grating_s_params` group accepts this exact patch.

Primary product references:

- [Frequency-domain monitor](https://optics.ansys.com/hc/en-us/articles/360034902393-Frequency-domain-monitor-Simulation-object)
- [adddftmonitor script command](https://optics.ansys.com/hc/en-us/articles/36957320687763-adddftmonitor-Script-command)
- [Metamaterial S-parameter extraction](https://optics.ansys.com/hc/en-us/articles/360042095873-Metamaterial-S-parameter-extraction)
- [Extend structures through PML boundaries](https://optics.ansys.com/hc/en-us/articles/360034382414-Always-extend-structures-through-PML-boundary-conditions)

Official mechanism references:

- [Analysis Groups](https://optics.ansys.com/hc/en-us/articles/360034382454-Analysis-Groups-Simulation-object)
- [adduserprop script command](https://optics.ansys.com/hc/en-us/articles/360034928733-adduserprop-Script-command)
- [getnamed script command](https://optics.ansys.com/hc/en-us/articles/360034408574-getnamed-Script-command)
- [setnamed script command](https://optics.ansys.com/hc/en-us/articles/360034928793-setnamed-Script-command)
- [runsetup script command](https://optics.ansys.com/hc/en-us/articles/360034928893-runsetup)
- [save script command](https://optics.ansys.com/hc/en-us/articles/360034410814-save-Script-command)
- [Script Commands as Methods in the Python API](https://optics.ansys.com/hc/en-us/articles/360041579954-Script-Commands-as-Methods-Python-API)

## Finding

The 804.347826 nm observation is nearest-mesh-cell displacement, not a
local-to-world conversion defect. MetaCraft's deterministic repair candidate
appends one marked `specified position` invariant to the parent group's setup
script, runs group setup, reads the internal `T` setting back, and continues
to validate the dataset's world z coordinate against the declared
transmission plane. The official documentation supports this extension seam,
but installed-version acceptance of the candidate remains pending one
separately authorized Native gate at a new application root. The candidate is
a project contract, not a verified product fact. No coordinate offset and no
wider validation tolerance are justified.

## Project policy input

The product evidence does not choose MetaCraft's coverage distances. The
owner-approved periodic template policy is recorded separately in ADR 0017:
the substrate/interface/meta-atom vocabulary, outward 100 nm placement grid,
minimum substrate height, fixed 100 nm plane clearances, and the source,
reflection, transmission, and solver bounds. Those values are conservative
template policy and remain subject to native qualification.
