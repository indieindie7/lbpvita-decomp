# LBP Vita: how the level edit tools (Poppet / create mode) work

Source: Ghidra decompile of eboot (names-only project). Addresses are eboot VAs.
"read" = seen in the decompile. "guess" = inferred, not checked. State: 2026-11-14, second pass (layers, unphysics, wiring added).

## Index
1. Big picture
2. State stack and messages
3. Input and picking
4. Action queue and undo
5. Shape data
6. Vertex editor (corner edit)
7. Slice
8. Glue
9. Flood fill (material change); 9a vertex move, 9b layers, 9c unphysics, 9d wiring, 9e joints and stamp
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

## 9a. Vertex move (read)
- 0x813140c2. BP_NEXT_VERTEX = button 0xc, BP_PREVIOUS_VERTEX = 0xd (both repeat while held). BP_PLACE_HERE (button 9) commits the moved vertices with 0x810ec580(shape, verts, loops, 0).

## 9b. Layers and thickness (read)
- Grab state update 0x8131069e. Held things = vector at state+0x88 (count +0x8c), 0x24 bytes each: +0xc thing, +0x18 back depth, +0x1c front depth (integers).
- 0x81337638 = lowest back of the held set, 0x813376a2 = highest front.
- Depth units: layer pitch 200, thick layer 180 deep, thin layer 20 deep. Layer back planes: -510, -310, -110, 90. Allowed range: back >= -510, front <= 110.
- 0x8130d510(state, forward, thickness, thinStep) = one layer / thickness step:
  - step is 200, or 20 when thinStep is set and the shape material type (shape +0x124) is not 6..11;
  - new thickness is clamped to at least 20, or at least 180 for material types 6..11 and for multi-selections (0x81337982);
  - a thin thing that grows goes straight to 180; a thing that shrinks to 20 snaps to the nearest layer back plane;
  - the move is refused when the free room in front or behind (0x81339a26 sweep, start 1000000) is too small;
  - on success: sound poppet/changelayer, then 0x8133770e applies it.
- 0x8133770e(world, held, front, back, ...): turns the request into a delta, rounds it to a multiple of 200, pulls it back inside -510..110, then sets each held thing with 0x8133d024(world, entry, front + d, back + d).
- Prompts BP_CHANGE_LAYER / BP_CHANGE_LAYER_THICKNESS are shown on button 0xf. Last used front / back are kept in globals 0x8186551c / 0x81865518 (guess: so the next object starts on the same layer).

## 9c. Unphysics (read)
- 0x8132decc(state, button). Selection = vector at state+0xd0 (0xc bytes each, count +0xd4). Empty selection + button 9 = error sound.
- It is a toggle: if every selected thing is already unphysics (0x8122bed4) the tool turns physics back on (sound dephys_undo), otherwise off (dephys_activate).
- Steps: undo snapshot 0x8113036c; for each selected thing collect its group (0x810e8896); for each member call 0x8122be3c(member, on, 1) and set or clear bit 8 of the 16-bit flags at thing+0x78; register the thing with the Poppet (0x8113c85c).
- First activation also reports a hash id 0x8a9e3e57 to the player record (guess: tutorial or pin progress).

## 9d. Switch wiring (read in part)
- 0x81328388. State fields (int index): [0x2d] the switch thing, [0x30] output index in use, [0x31] thing connected now, [0x34] its port.
- Switch part: +0x30 type, +0x34 output array, +0x38 output count. Type 0x13 has a growing output list: when the current output is taken, a new one is added (0x810f8a5c(switch, count + 1)) and empty ones are removed afterwards (0x810f8728).
- Connect (button 9 or touch 0x51 over a valid target, prompt BP_PLACE_SWITCH_HERE): undo snapshot; 0x810fe578(output, target, port, 0) tests the link; the old link is removed and the new one made with 0x810fd908(output, thing, port); both things go into an edit list sent through 0x8113c75c; sound poppet/connect_switch.
- Released over nothing: a helper thing is spawned from a resource (0x81195470) at the cursor and a 0xf4-byte state (ctor 0x81305e74) takes over (guess: the wire end becomes a placed object).
- BP_DELETE_SWITCH (button 0xb): undo snapshot, remove the link (0x810fd908), sound poppet/deleteobject, pop the state. Button 10 = cancel.

## 9e. Joints and place / stamp (call skeleton only)
- Joints 0x8131cad4: prompts BP_PLACE_JOINT or BP_ATTACH_JOINT (button 9), BP_DETACH_JOINT / BP_DELETE_JOINT (0xb). Commit = undo snapshot, then 0x8131aeda(state, a, b); on failure the snapshot is dropped. Helpers 0x8131a01e, 0x81319f78, 0x8131a0c4, 0x8131a20a pick the two things and the joint end.
- Place / stamp 0x81307f28: BP_PLACE_HERE (9) -> placement test 0x81343346, on success sound poppet/createstamp, on failure poppet/error_3d; BP_DELETE (0xb); BP_HIDE / BP_SHOW on button 0x3b. Commit path: undo snapshot, 0x81307ca2(state, thing), snapshot dropped on failure.
- 0x812f9db0 is not the save itself: it is the thermometer / saving notification (voice lines vo_create_saving, vo_create_thermo).

## 9f. Joints, detail (read)
- A joint is itself a thing; while placing, it is the held thing (state+0x88 list). Its joint part: +0x18 = thing on end A, +0x24 = thing on end B, +0x144 / +0x148 = two settings kept across a re-attach.
- 0x8131a01e = end A is inside the held set, 0x81319f78 = end B is, 0x8131a0c4 = the attached thing, 0x8131a20a -> 0x81344612 = that end is fixed.
- Commit 0x8131aeda(state, target, pos): no valid target -> the joint just drops (state vtable +0x94, +0xb4, then 0x8113fda8 registers it). With a target: 0x813459a2(jointThing, target, endIsB) attaches the free end, 0x810c5c38(joint) rebuilds it, the group of the old end is re-registered (0x81130fc8). A joint with one end already fixed continues as "place second end" (0x811406ce).
- Bolts on a glued target: flag 8 is set on target part +0x20 word +0xc and the shape is rebuilt (0x810ed21e, 0x810ed1b8) (guess: bolt hole / static mark).

## 9g. Stamp commit (read)
- 0x81307ca2(state, parent): for every held thing whose type byte (thing+0x7e) is 0x42 the switch outputs that point outside the stamped set are relinked with 0x810fe578; then state vtable +0x98 does the actual drop; then the parent thing gets 0x810bbdba (guess: refresh of the group it lands on). Returns 0 when the drop is refused.

## 9h. Delete vertex (read)
- In 0x81315fee: BP_DELETE_VERTEX on button 0xb (touch variant 0x52). Undo snapshot, thing registered (0x8113c85c), vertex vector copied from shape +0x108.
- The positions of the neighbours (previous of the first selected, next of the last selected, index wrapped with 0x81543dc4) are kept so the cursor can jump to one of them afterwards (0x8131280c).
- Each selected index goes through 0x813131f8(state, index, verts, loops): erase the 16-byte vertex, find the loop that owns it and take 1 from its count. For a loop that is not the first one, when the area test 0x8112a6d2 passes the whole loop is removed from both vectors and the function returns 1, which stops the pass (guess: a hole that collapsed is dropped whole).
- Then the usual set-polygon; if nothing is left selected the editor leaves (0x81312a62).

## 9i. Cut / slice boolean (read)
Three stages in the range 0x8140b000..0x8140d000, all on one node array (0x20 bytes per node: x, y, z, w, +0x10 own index, +0x14 prev, +0x18 next, +0x1c output link, -1 = not linked).
- 0x8140c16e Bool_AddPolygon: copies one polygon (vertices plus loop counts) into the node array as closed prev/next rings. Flag = subtract: the vertex order is reversed, so the cutter has opposite winding. A non-zero tolerance first grows or shrinks the polygon (0x8140bf6c).
- 0x8140ba38 Bool_Sweep: sweep line. Nodes are sorted, then visited in order; an active edge list (0x2c-byte list nodes: start, end, winding count +0x10, direction +0x14) holds the edges the line crosses. Each vertex is a start (both neighbours later: two edges added, winding taken from the edge beside it), a pass (one edge replaced) or an end (two edges removed). Edges whose winding count is 0 are the boundary of the result and get their +0x1c link written. Crossing edges are split by 0x8140b93e.
- 0x8140c306 Bool_EmitLoops: follows the +0x1c links and writes each chain as one output loop. With a tolerance it cleans the result, tests it (0x8112b2b0) and re-runs the two stages once.

So material cutting is a winding-number polygon boolean, not a triangle clipper.

## 9j. Glue pair (read)
0x81418114 Glue_TryPair(shapeA, shapeB, world, flags):
- both shapes need bit 0 of the u16 at +0xc0 (glueable);
- same body (+8 -> +100) and already listed: returns 1, nothing to do;
- flag 2: measures the gap with 0x810e8322 and refuses when it is over 0.5;
- adds each shape to the list of the other at +0xa4 (0x81417e44), type 1, or type 2 with flag 8;
- unless flag 1, asks the world (+8 -> +0x54) to rebuild (0x8133504e).

## 9k. Undo / redo (read)
Undo is whole-level snapshots, not per-action records.
- 0x8123d0dc Undo_PushSnapshot: makes a resource of type 9, serialises the current level into it (0x81130b9c), drops every snapshot after the cursor (the redo tail) and appends. Then it trims from the oldest end while there are more than 0x80 snapshots, or more than 1 and the pool reports over 0x200000 bytes (2 MB).
- List head DAT_818f1004, count DAT_818f1008, cursor DAT_818f0ff8, saved marker DAT_818f0ffc.
- 0x8123d7b8 Undo_StepBack and 0x8123d8c8 Undo_StepForward move the cursor and load that snapshot with 0x81212cd4 (the level deserialiser), then refresh the world. Return 0x66 = nothing to step to, 0x77 = busy.
- 0x8123d502 Undo_EnsureCurrent pushes a snapshot of the present state before the first step back, so redo can return to it.
- 0x8123cf9e Undo_Clear, 0x8123cffc Undo_DropNewest, 0x8123d054 Undo_IsAtSavedState, 0x8123da08 Undo_CanUndo (create mode 4 or 5 only, and not while any part reports state 5).

## 9l. Scale / rotate of the held set (read in part)
0x8130e890 is the per-frame update of held objects (tool mode at +0xb0; modes 7 and 8 leave early).
- Stick input goes through 0x81145a14 (grid aware, uses floorf), giving an angle step and a scale factor.
- 0x8130ce88 clamps the scale: it gets the smallest and largest allowed factor for the set (0x81145604 / 0x81145682) and replaces the factor when it would pass either; a factor of exactly 1.0 means no scaling this frame.
- 0x8130d0d6 quantises the rotation when the grid is on or a part of the set is a snapping kind.
- With the grid on and no stick angle, the step becomes 1.5707964 (90 degrees) about the centre of the bounds of the set (0x81337b9e).
- Prompt on button 9: BP_SCALE_ROTATE when the set can scale (0x8130c33c), else BP_ROTATE.

## 9m. Stickers and decorations (commit read)
- Sticker: 0x813265da Sticker_Commit calls 0x8121a488 (paints the sticker onto the target thing; body not dumped). Sound poppet/placesticker with pitch 1 - log(sqrt(w * h + 1) * 0.0033): big stickers sound lower.
- Decoration: 0x81303a62 Decoration_Commit calls 0x814212fe (attaches the decoration to the target; body not dumped).
- Both then record the item as used (0x810b49ba), notify the target (0x813028d4) and, unless a keep-holding flag is set, drop the held item (0x8113c206). Failure takes the error path 0x81130f7a.
- Inside (skeleton): 0x8121a488 Sticker_PaintOnThing refuses when the target is locked (0x8134d316), adds the sticker to the target with 0x81143a32, then runs the sticker switch check (0x81142dda) and the first-use prize popup (0x8107075e, type 0x2e). 0x814212fe Decoration_AttachToThing does the same with 0x810a8cf2 and the switch check 0x81143352.

## 9n. UV tool (read in part)
0x8132d320: select a shape (poppet/object/select), then the stick pans the texture offset (step 0.002 times zoom, wrapped with fmodf 1.0) and rotates it (angle kept in -pi..pi at +0x38 of the UV record of the shape). Button 0xb = BP_RESET_UV_TOOL.

## 9o. Level save (call skeleton)
lbp_SaveLevelFart 0x8105764e: serialises the level with 0x81212cdc (the twin of the loader 0x81212cd4), queues it as the job "SaveLevelFart", then copies the slot record field by field and updates the slot map. 0x812f9db0 is only the on-screen thermometer / saving notice.
Both 0x81212cd4 and 0x81212cdc are 8-byte thunks into the resource system: load = 0x8119b6c6, save = 0x8119b89e. Undo snapshots and the level file use the same pair, so an undo step is a level load from memory.

## 9p. Thing tree (read in part)
0x8122aef6 Thing_SetParent(thing, newParent, flag): things form a tree. +0x50 parent, +0x48 first child, +0x4c next sibling, +0x5c group root, +0x64 body id of the root, +0x28 a physics link that is refreshed (0x810dfbe8) on reparent. The call unlinks the thing from the sibling chain of the old parent, pushes it at the head of the child list of the new one, sets the root pointer (0x8122a6ee) and walks the whole subtree to fix +0x5c. Glue, joints and stamps all end in this call. Rest of the range 0x8122a000..0x8122c400 (38 functions, decomp_thing.c) not read.

## 9q. Parts on a thing, sticker and decoration add, resource load / save (read)
A thing keeps its parts as a bitmask at +0x10 / +0x14 (up to 0x27 part kinds) with a slot table at +0x34 (slot = kind * 4) or, for sparse things, up to 4 inline slots at +0x38 indexed by 2-bit fields at +0x18 / +0x1c. Direct pointers: +0x20 body (kind 0), +0x28 position (kind 4), +0x2c shape (kind 0x12), +0x24 render mesh.
- 0x8122bb30 Thing_AddPart(thing, kind, arg): no-op when the bit is already set; else allocates the part (0x812307ec), wires the position pointer into body +0xe8 and shape +0xe4, registers a new body with the world, and marks the thing dirty (+0x78).
- Kinds seen in use: 0 body, 2 world, 3 render mesh, 4 position, 0xf stickers, 0x10 decorations, 0x12 shape, 0x1a (handed to the world at +0xc). These numbers match the part order known from the PS3 games; only the ones listed are checked here.
- 0x8122b8d4 Thing_IsValid: every float of the two 4x4 matrices in the position part (+0x20, +0x60) must be finite (0x813a3d90), the bounds must pass 0x8122966e, and a thing with no parent needs at least one part other than position.
- 0x81143a32 Stickers_Add(id, thing, ...sticker): 0x81143964 adds part 0xf if missing and records the plan as used (0x810b49ba), then 0x810f0c58 appends the sticker record to the part. Sticker record: +0x20 / +0x24 centre (shifted by half the size along both axes), +0x3e u16 id, +0x42 kind (2 = eyetoy / photo sticker, gets its texture from 0x810f0e06).
- 0x810a8cf2 Decorations_Add(id, plan, thing, ...): needs a plan with a mesh (+0xe8), adds part 0x10 if missing, then 0x810a8740 does the attach.
- 0x8119b6c6 Resource_Load: under the resource mutex (DAT_818e5b00), only for load state 0 or 4..5 (byte +0x3d); state 3 while loading; makes a 0x178-byte reader, runs the deserialiser 0x81212b94, then state 4 on success or the error path 0x811997ac. Load time is summed into DAT_818e5a90.
- 0x8119b89e Resource_Save: only for state 4..5; state 5 while 0x81213470 serialises, then back to 4. Both return 0x72 when refused.
- Joint placement 0x8134465c (not named): works on end A (+0x18) and end B (+0x24), joint type 1..6 at +0xc, compares an angle at +0x7c of each end with 90 and 180 and moves the ends with 0x810dfbb0. Purpose of the angle test not determined.

## 9r. Sticker list, decoration record, glue gap, joint ends, resource reader (read)
- 0x810f0c58 Stickers_Append(part, sticker, slot, outChanged): the stickers part has one list at +0xc and per-slot lists at +0x18 + slot * 0xc (slot -1 = the main list); records are 0x58 bytes. A normal sticker (byte +0x43 clear) first removes every record with +0x43 set; then the oldest records are dropped (0x810f066e) while the list is at its cap (cap from 0x810f08e4), and the new one is appended. So stickers per surface are capped and the oldest goes first.
- 0x810a8740 Decorations_Attach: decoration records are 0x78 bytes in the list at part +0xc (count +0x10): 4x4 matrix at +0, render instance at +0x40, plan id u16 at +0x6c. Moving a decoration that already sits on another thing copies its record, removes it there (0x810a7b44) and re-adds it here; a new one gets a 0x80-byte render instance (0x810dbf82). Scale is halved when the target has part 6.
- 0x810e8322 Shape_MinGap(shapeA, shapeB, outA, outB): for every convex piece of A (+0x114, count +0x118) against every piece of B, 0x810e5b10 gives two distances and the minimum of each is kept. This is the gap that Glue_TryPair compares with 0.5.
- 0x813459a2 Joint_AttachEnd(angle, joint thing, target thing, end): needs the joint part (kind 1) and a target with a shape; end 0 goes through 0x810c4d58 (set end A, +0x18), end 1 through 0x810c4db8 (set end B, +0x24). The joint keeps a per-end angle offset at +0x54 / +0x58 and a local anchor at +0x34.. / +0x44..; re-attaching an end zeroes its anchor.
- 0x81212b94 Resource_Deserialise: sniffs the header (0x81211efe); binary goes to 0x81212288, text to 0x816067d8, then calls the resource vtable slot 0 (post-load). 0x81212288 switches on the resource type byte (+0x3c, 1..0x29 and up) to pick the reflection function from a table at 0x816079b4 (8 bytes per type) and runs the generic reader 0x81240d52. Unknown type returns 0x6d. 0x81213470 is the writer twin (not read).

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
- Joint placement 0x8134465c (angle test against 90 / 180 not understood) and the rest of decomp_joint.c.
- Thing 0x8122ab62 (walks parents by kind byte +0x7e), 0x8122c012.
- The writer 0x81213470, the generic reflection reader 0x81240d52, the per-type reflection table 0x816079b4.
- Piece-pair distance 0x810e5b10, sticker removal 0x810f066e, script native RequestSaveLevel 0x811ed4b0.
- Class trees are in CLASSES.md (Poppet tool states sit under PickState 0x8185b62c; each constructor passes its SUBMODE number). Unnamed classes there still need reading.
- Library identification (FMOD, libpng); libult and steroid suprx modules.
