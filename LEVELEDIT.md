# LBP Vita: how the level edit tools (Poppet / create mode) work

Source: Ghidra decompile of eboot (names-only project). Addresses are eboot VAs.
"read" = seen in the decompile. "guess" = inferred, not checked. State: 2026-11-14, first pass.

## Index
1. Big picture
2. State stack and messages
3. Input and picking
4. Action queue and undo
5. Shape data
6. Vertex editor (corner edit)
7. Slice
8. Glue
9. Flood fill (material change)
10. Function map by tool
11. Not read yet

## 1. Big picture (read)
- Each player has one Poppet object. A tool is a C++ state object. Starting a tool = `new` + constructor + push on the Poppet state stack. Leaving = pop.
- The menu and scripts do not call tools directly: they send a message id (`E_POPPET_*_MESSAGE`, 89 ids, enums.txt) to `Poppet_HandleMessage` 0x812fcb1a, a switch that builds the state.
- A state does not change the world directly either: it builds a small action object and queues it on the Poppet (0x81134022). The action virtual slot 4 runs it at once and the Poppet is marked dirty (+0x948).
- Before any destructive edit the state calls 0x8113036c, which snapshots the level for undo.

## 2. State stack and messages (read)
- Push 0x8113c1f8 (Poppet vtable +0x40), pop-if-top 0x8113c206 (+0x44, top = +0x3c). Operator new 0x8100cf40.
- State layout: +0x00 vtable, +0x10 owner (owner vtable +8 = get Poppet, +0x14 = get player/pad).
- Message -> constructor (object size):

| id | message | ctor | size |
|---|---|---|---|
| 0 | CURSOR | 0x81322bb6 | 0x110 |
| 1 | PLAN | 0x81300ec0 | 0x11c |
| 4 | PHOTO | 0x813190b2 | 0xdc |
| 9 | PICK_DECORATIONS | 0x813043c2 | 0xbc |
| 10 | EDIT_VERTS | 0x81317b86 (flag 0) | 0xbc |
| 60 | SLICE_N_DICE | 0x81317b86 (flag 1) | 0xbc |
| 15 | FLOOD_FILL | 0x813180b0 + 0x8131825a | 0x140 |
| 41 | STICKER_CUTTER | 0x81327560 (0) | 0x138 |
| 58 | STICKER_WASH | 0x81327560 (1) | 0x138 |
| 43 | GLUE | 0x813185d0 | 0xd4 |
| 44 | EDIT_UV | 0x8132dbca | |
| 45 | UNPHYSICS | 0x8132ddd4 | |
| 82..86 | DANGER unlethal / electric / fire / plasma / gas | 0x81301898 (kind 0, 2, 1, 0xd, 6) | 0x114 |

## 3. Input and picking (read)
- Button test: 0x81052af6(pad, button, prompt text, 0) = pressed this frame, and shows the prompt (BP_* string). 0x81052bd0 = held. Buttons seen: 9 select, 0x51 touch select, 10 back, 0xb unglue/delete, 0x52 touch variant, 0x3f.
- Pick-state base class (vtable 0x8185b62c, ctor 0x81471f44, update 0x81471fa0): used by every "choose an object first" tool.
  - tap on a thing: queue action 0x40 with the thing uid (0x812fbdc4);
  - finger moved more than 10 px: start a marquee (action object 0x30 bytes, vtable 0x81859080);
  - finger up after a marquee: action 9.
- EDIT_VERTS / SLICE state (0xbc bytes) is only this pick step. The chosen thing then gets the real editor state (section 6).

## 4. Action queue and undo (read; purpose = guess)
- 0x81134022(poppet, action): append to the vector at poppet+0xc10, call action vtable +0x10 (action, poppet, 0), set poppet+0x948 = 1.
- 0x812fbdc4(poppet, type, arg): generic action, 0xd8 bytes, type at +0xc8, arg at +0xd0.
- Guess: actions exist so edits replay the same way for every player online.
- Undo: 0x8113036c checks 0x8123da08(1,0), then calls 0x8123d0dc(level) = store a snapshot of the whole level (timed with the process clock). 0x81130f7a -> 0x8123cffc = drop that snapshot when the edit fails (seen after a failed glue). So undo = level snapshots, not per-tool inverse steps.

## 5. Shape data (read)
- Thing +0x28 = position part, +0x2c = shape part, +0x64 = rigid group root (two things with the same +0x64 are already one glued body).
- Shape part: +0x88 polygon vertex vector (16 bytes per vertex, x y z w), +0x94 loop vector (one int per loop = its vertex count), +0x108 pointer and +0x10c count of the vertices the editor draws and hit-tests.
- 0x810e7efa(shape, verts, loops, 0, ...) = set a new polygon and rebuild.

## 6. Vertex editor (read)
- Hover / select / add: 0x81314cbe. Move, next, previous: 0x813140c2. Delete: 0x81315fee.
- Editor state fields: +0xf8 selected vertex indices (count +0xfc), +0x114 and +0x120 backup copies of the vertex and loop vectors taken before each edit, +0x12c box-select active, +0x130/+0x134 box anchor, +0x1c lasso object (0xa8 bytes, 0x81321d2c; point test 0x81322acc), +0x174 slice mode.
- Select: tap a vertex, or drag a box (every vertex inside the rectangle), or lasso. A box smaller than 8 units squared leaves the editor when the shape check 0x810ed85a fails.
- Add a vertex: select on an edge with no vertex under the cursor -> 0x813132f0(state, edge index): copy verts and loops, turn the cursor point into shape space (0x8172b3bc with thing +0x28), insert after the first vertex of that edge, add 1 to the loop that owns it, call set-polygon. Returns the new index, which becomes the selection.
- Sounds mark the steps: poppet/object/selectvert, addvert, deletevert, rolloververt.

## 7. Slice (read in part)
- Same editor with +0x174 set; cut points are added with BP_ADD_SLICE_POINT (0x813133fc).
- Commit: 0x81312b74. Checks the cut line (0x81348ad6), then calls 0x81141592 (preview path 0x81141452).
- 0x81141592, the cut itself:
  1. back up the shape verts (+0x88) and loops (+0x94);
  2. build a polygon from the cut points (0x8140c16e, 0x8140ba38);
  3. polygon boolean 0x8140c306: shape minus cut -> new verts and loops;
  4. signed area (0x8112a7ae) must be >= 0, then the result is set on the shape (0x810ec580);
  5. if the result now overlaps a neighbour (0x810eb936) the backup is restored with set-polygon;
  6. 0x810e7f98 turns each separate loop into its own thing. Empty pieces are dropped and every piece is registered with the Poppet (0x81130fc8).
- So a slice is a boolean subtract of a thin cut polygon, not an edge split.

## 8. Glue (read)
- State 0xd4 bytes, update 0x8131868c. Two thing lists: +0xbc = group under the cursor (filled by 0x81133380 = collect the glued group of a thing), +0xc8 = first pick.
- Step 1 (prompt POPPET_GLUE_FIRST): select -> the hovered group becomes the first pick.
- Step 2 (POPPET_GLUE_SECOND): the hovered thing must be in another rigid group. On select: undo snapshot, then for every pair (first group, second group) 0x810e8322(shapeA, shapeB, &a, &b) must give a <= 0.5 and b <= 20.0 (meaning of a and b = guess: gap and depth distance), and 0x81418114 must pass. The first pair that passes is glued through 0x8113c75c (queues on poppet+0xf38). No pair: error sound and the snapshot is dropped.
- BP_UNGLUE (button 0xb) appears when the hovered thing shares a group with another thing in the list.

## 9. Flood fill = change material (read in part)
- Action handler 0x8132a2ec builds a temporary flood-fill state and calls 0x8131833e per thing: set the new material on the render part (0x810b5366), pick one of two defaults when shape +0x7c == 10.0 (guess: bevel by thickness), rebuild (0x810ed0f4), play poppet/floodfill.

## 10. Function map by tool (from strings; bodies not read unless listed above)
| addr | what |
|---|---|
| 0x81307f28 | place object / stamp (BP_PLACE_HERE, createstamp) |
| 0x8131069e | grab: change layer, thickness, glue on drop, delete |
| 0x8130e890 | scale / rotate held object |
| 0x8130d510 | change layer |
| 0x812fdbb4, 0x8131cad4 | joints: bolt, spring, wobbler, motor; attach, detach |
| 0x81328388 | switch wiring (connect_switch) |
| 0x81325c4c, 0x813265da, 0x81326b56 | stickers |
| 0x81303a62, 0x81303e4a | decorations |
| 0x8132d320 | UV tool |
| 0x8132decc | unphysics (dephys_activate / dephys_undo) |
| 0x81301990 | danger (lethalise / unlethalise) |
| 0x8134f652 | costume save / reset / random |

Full list: ghidra/work/poppet_strs.txt.

## 11. Not read yet
- Move / delete vertex bodies, the cut maths (0x81141592), the glue test maths (0x810e8322), place / stamp, grab, joints, wiring, stickers, UV, save path (vo_create_saving 0x812f9db0).
