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

## 9s. Joint end depths, thing slots, writers, sticker removal (read)
- 0x8134465c Joint_FitEndDepths(joint, hit, changedCount): the 90 / 180 numbers are depths, not angles. For the shape at each end it reads the depth value d at +0x7c and the centre c = (+0xf0 + +0x100) * 0.5. Both d under 180: both end offsets are 0. A wholly in front of B (cA - dA >= cB + dB): offset A = 90 - dA, offset B = dB - 90. A wholly behind B: the signs swap. Equal depths that overlap: both 90 - d. Different depths that overlap: the shape with the smaller d sets the offset and its point is carried into the space of the other shape (0x8172b3bc). An offset is forced to 0 for a shape with d under 180. Results go to joint +0x3c (end A) and +0x4c (end B); the count of changed ends is returned through the third argument. So a joint end on a deep shape is pulled to 90 from the face that looks at the other shape.
- 0x8122c012 Thing_SetRefSlot(thing, value, index): pointer vector at thing +0x60; grows it to the index, stores, trims empty slots from the end, frees the vector when it is empty, then marks the thing dirty in the world (+0xc) and in the dirty byte table (world +0x2a8, index = u16 at part +0x28).
- 0x8122ab62 Thing_UpdateBoardHidden: recomputes the byte +0x7f of a thing from its object type +0x7e and its parent (+0x50) chain; see 9zb.
- 0x81213470 Resource_Serialise(res, out, opts): frees the old buffer; opts[0] is the mode (3 = pick by resource type with 0x8119f97e). Mode 1 = binary writer 0x81212ce4. Mode 5 = 0x81607188 Resource_WriteMode5, a stream writer (vtable 0x8183fd04) that emits marker words 0xe2030000 and 0x84003144 before the body 0x816ca078.
- 0x81240d52 Resource_ReadWithHeader: optional 4 byte magic, then a header parsed by 0x8123f9e0; when the hash in the header equals res +0x44 the body is skipped (already current), else the dependency range is loaded (0x8124028c) and the body read (0x81240b72).
- 0x810f066e Stickers_RemoveRange(part, first, count, list, otherList, markOnly, onlyFlagged): list -1 = the main sticker list at part +0xc, else the list at part + list * 0xc + 0x18; records are 0x58 bytes. Each removed record frees its 0x70 byte slot in the table at part +0xe4 (index u16 at +0x3c) and every higher index in both lists moves down by one. markOnly sets byte +0x44 on the records in place of erasing. Then the render caches of the world are marked dirty.
- 0x810e5b10 Shape_PairDistance(a, b, outDist, outInfo): radius at +0x38 of each shape. Both 0: polygon against polygon (0x811292b0), distance = separation along the returned axis. One with a radius: closest point of each polygon edge to the centre of the round shape.
- native_RequestSaveLevel 0x811ed4b0 only calls 0x8107b0b2; native_DoPreSaveLevelCheck 0x811ed4b8 calls 0x8107b0de (bodies not read).

## 9t. Save request path (read)
- native_RequestSaveLevel 0x811ed4b0 -> Game_RequestSaveLevel 0x8107b0b2: takes the game object (DAT_818e56ec), reads the current slot id (0x81179814) and calls 0x811810d6 Game_SendSaveLevelMsg(game, slot, 1).
- Game_SendSaveLevelMsg only acts on slot type 2. It first walks 0x21 budget records (0x14 bytes each, at +0x8c0 of the local player record; used +4, limit +8, flags +0xc): if one is over its limit it shows the notice 0x812fae18 and returns without saving. Otherwise it builds network message 0x37 through the session object DAT_819077ac (0x812c2896 / 0x812c27f8) with the slot id as payload. So the save itself is done by the handler of message 0x37, on every peer, not by the caller.
- native_DoPreSaveLevelCheck 0x811ed4b8 -> Game_DoPreSaveLevelCheck 0x8107b0de -> 0x81183706 Game_PreSaveCheck(game, flag): when the world byte +0x60 is 0 it scans the thing list of the world (+0x14 array, +0x18 count); a thing with object type +0x7e of 7 (OBJECT_MOVINATOR) or 0x84 (OBJECT_POWERUP_MOVE) opens a three-string dialog (0x8107075e, dialog 0x62 or 0x63, text keys 0x7832f029 / 0x9d9c76e9 / 0x56eda7e1) and returns 0 = do not save.
- 0x8118128c (next to it, read in part) fills a type 9 resource descriptor from the level resource (+0x84 of the game), the same type the undo snapshots use.
- Message 0x37 is E_MESSAGE_TYPE_SAVE_LEVEL in the message type enum. The job stepped by 0x810587da is a level download job (9ze), not the editor save: DownloadJob_Step (job state +0x28, 1 = running): pending work at +0x3c goes to 0x810585ec, a slot index at +0x38 other than -1 goes to 0x81058472; otherwise it scans the per-peer status array (+0x1c, count +0x20): any 0 = wait (0x81058148), any 1 = 0x810580b0, all higher = lbp_SaveLevelFart 0x8105764e (section 9o). State 2 or 3 returns 1 = finished. Callers 0x810589fc and 0x81058c8e (not read).

## 9u. Reflect function per resource type (read)
0x816079b4 is not a table but a row of 8-byte thunks, one per resource type (type n at 0x816079b4 + (n - 1) * 8). The binary reader 0x81212288 and the writer pick the thunk by the type byte +0x3c of the resource; each thunk calls the reflect function of that type, which visits the fields for load and for save alike. 0x812142c8 is shared by the types with no reflected fields (raw payload). The row was read for types 1..30; later types use another code shape and were not listed.

| type | name | reflect function |
|---|---|---|
| 1 | RTYPE_TEXTURE | 0x81546408 |
| 2 | RTYPE_MESH | 0x8167f730 |
| 3 | RTYPE_PIXEL_SHADER | 0x812142c8 |
| 4 | RTYPE_VERTEX_SHADER | 0x812142c8 |
| 5 | RTYPE_ANIM | 0x81682f80 |
| 6 | RTYPE_GUID_SUBST | 0x816dea10 |
| 7 | RTYPE_GFXMATERIAL | 0x81686b6c |
| 8 | RTYPE_SPU_ELF | 0x812142c8 |
| 9 | RTYPE_LEVEL | 0x816d6180 |
| 10 | RTYPE_FILENAME | 0x812142c8 |
| 11 | RTYPE_SCRIPT | 0x816f2c64 |
| 12 | RTYPE_SETTINGS_CHARACTER | 0x816884ac |
| 13 | RTYPE_FILE_OF_BYTES | 0x812142c8 |
| 14 | RTYPE_SETTINGS_SOFT_PHYS | 0x816d3018 |
| 15 | RTYPE_FONTFACE | 0x812142c8 |
| 16 | RTYPE_MATERIAL | 0x81677030 |
| 17 | RTYPE_DOWNLOADABLE_CONTENT | 0x816a647c |
| 18 | RTYPE_EDITOR_SETTINGS | 0x8169275c |
| 19 | RTYPE_JOINT | 0x816dfb78 |
| 20 | RTYPE_GAME_CONSTANTS | 0x816cd05c |
| 21 | RTYPE_POPPET_SETTINGS | 0x816898ac |
| 22 | RTYPE_CACHED_LEVEL_DATA | 0x816a4650 |
| 23 | RTYPE_SYNCED_PROFILE | 0x816a7220 |
| 24 | RTYPE_BEVEL | 0x816757e0 |
| 25 | RTYPE_GAME | 0x81690c98 |
| 26 | RTYPE_SETTINGS_NETWORK | 0x816d470c |
| 27 | RTYPE_PACKS | 0x816a4e80 |
| 28 | RTYPE_BIG_PROFILE | 0x816b6728 |
| 29 | RTYPE_SLOT_LIST | 0x816a3e74 |
| 30 | RTYPE_TRANSLATION | 0x812142c8 |

For level editing the ones that matter are LEVEL (the world and all things), JOINT, MATERIAL, BEVEL, POPPET_SETTINGS and EDITOR_SETTINGS. Full list: ghidra/rtype_reflect.txt.

## 9v. Level resource fields (read)
Reflect_Level 0x816d6180(visitor, level). Every field is registered by name, so the reflect functions give the file layout directly:
- 0x81606074(visitor, level + 0x58): the world reference (the thing tree hangs off it); a non-zero result aborts.
- PlayerRecord +0x64 (type 0x10, element reflect 0x816e3d90), TutorialInventory +0x40 (type 0x15, 0x816a7bbc), TutorialInventoryData +0x4c (type 0x15, 0x816e3ecc).
- TutorialInventoryActive +0x588 and CopiedFromSomeoneElse +0x58b (type 9 = bool).
- MusicGuid +0x574 and MusicSettingsGuid +0x578 (type 0x57 = guid), MusicStemVolumes_0..2 +0x57c (type 8 = float, 3 entries).

Field registration calls: 0x815ba3d4 Reflect_AddField(visitor, name, ptr, type code, element reflect function), 0x812414ea / 0x81241548 fill one 0x50-byte field record after 0x815ba36c grows the record array at visitor +0x14. A scan of every call to these three with its name string and offset gives the layout of all reflected structs: tools/fields.py, output FIELDS.md (259 functions, 1857 fields).

## 9w. Level-edit structs from the reflect tables (FIELDS.md)
Field names are the strings the game itself registers (Reflect_AddField 0x815ba3d4), offsets are the pointer argument minus the struct base. Struct names marked (guess) are chosen from the field set, not from a string.

### Thing: Reflect_Thing 0x81664b50
The object record of the level. Header: UID +0x70, Parent +0x50, GroupHead +0x58, CreatedBy +0x74, ChangedBy +0x76, PlanGUID +0x6c. Then one optional part per slot, registered in this order (the offset is computed per part, so FIELDS.md shows +0x0):
PBody, PJoint, PWorld, PRenderMesh, PPos, PTrigger, PYellowHead, PAudioWorld, PAnimation, PGeneratedMesh, PLevelSettings, PSpriteLight, PScriptName, PCreature, PCheckpoint, PStickers, PDecorations, PScript, PShape, PEffector, PEmitter, PRef, PMetaData, PCostume, PCameraTweak, PSwitch, PSwitchKey, PGameplayData, PEnemy, PGroup, PPhysicsTweak, PNpc, PSwitchInput, PMicroChip, PMaterialTweak, PMaterialOverride, PInstrument, PSequencer, PControlinator.
39 parts. Everything the Poppet tools make is a Thing with some of these parts: a drawn shape = PShape + PBody + PPos + PGeneratedMesh, a bolt = PJoint, a sticker lands in PStickers of its target, a wire end in PSwitch / PSwitchInput.

### Joint: Reflect_Joint 0x816dfb78 (the PJoint part)
- Length: AllowExpand +0xc8, AllowContract +0xc9, ContractFreely +0xcd, LengthElasticity +0x88, LengthPlasticity +0x8c, LengthFunc +0x90.
- Angle: AngleDeviation +0x48, AngleElasticity +0x40, AnglePlasticity +0x44, AngleVelocity +0x4c, AngleFunc +0x50.
- NormalisedForces +0xca, DontRotateA +0xcb, DontRotateB +0xcc, BreakResistance +0xd0, GfxWidth +0xd8, EventNameAngle +0xf0, EventNameLength +0xe0.
One struct serves every connector the joint tool places (BP_PLACE_SPRING / WOBBLER / MOTOR / BOLT, 0x812fdbb4): the kind is the mix of length and angle settings, not a separate class per connector.

### Material: Reflect_Material 0x81677030
- Contact: Traction +0x60, IDensity +0x5c, Restitution +0x48, SlidingFriction +0x40, RollingFriction +0x44, Grabbable +0x59, ShiftGrip +0x70, TouchMoveable +0x5b, SoundEnum +0x6c.
- Forces: GravityMultiplier +0x64, AirResistanceMultiplier +0x68, MaxForce +0x54.
- Collision: CollideType +0x4c, CollideIgnore +0x50, Bullet +0x94, CompactMaterial.Limb +0x58.
- Edit rules: Dissolvable +0x71, DisableCSG +0x97 (blocks the cut / slice boolean of 9i), CircuitBoard +0x96.
- Breaking: Breakable +0x72, BreakMinVel +0x74, BreakMinForce +0x78.
- Explosion: Explodable +0x7c, CuttableByExplosion +0x95, ExplosionMinRadius +0x80, ExplosionMaxRadius +0x84, ExplosionMaxVel +0x88, ExplosionMaxAngVel +0x8c, ExplosionMaxForce +0x90.

### Bevel: Reflect_Bevel 0x816757e0
Vertices +0x50, Shared.AutoSmoothCutoffAngle +0x5c, Shared.TextureRepeats +0x60, Shared.SmoothWithFront +0x64, RelaxStrength +0x68, SubDivRadius +0x6c, FixedBevelSize +0x70, Spongy +0x74, IncludeBackFace +0x75. This is the edge profile the generated mesh of a drawn shape uses.

### Poppet tuning: Reflect_PoppetSettings 0x816898ac
All floats (type 8) unless noted.
- Stick: Deadzone +0x40, Bias +0x44 (int), MinSpeedFraction +0x48, AccelTime +0x4c, MouseStickScaleFactor +0x70.
- Speeds per tool: CursorSpeed +0x50, PaintSpeed +0x54, VertexSpeed +0x58, TranslateSpeed +0x5c, RotateSpeed +0x60, ScaleSpeed +0x64, PlanSelectScaleSpeed +0x68, PhotoSelectScaleSpeed +0x6c.
- Menu: CursorStringMaxLength +0x74, DPadRepeatRate +0x80 (int), MaxItemsPerPage +0x84 (int).
- Limits: WalkInputMultiplier +0x78, EdgeLimitMultiplier +0x7c, MaterialCostPerUnitArea +0xb0 (thermometer cost of drawn material), TopLevelPoppetScale +0xb4.
So cursor, paint, vertex, move, rotate and scale speeds are data, not constants in the tool code.

### Render mesh part: Reflect_PRenderMesh 0x81630ec0 (guess)
BoneThings +0x40, AnimPos +0x20, AnimSpeed +0x28, LoopStart +0x2c, LoopEnd +0x30, AnimLoop +0x60, EditorColour +0x10, DontCastShadows +0x5c, RTTEnable +0x5d, VisibilityFlags +0x5f (the BP_HIDE / BP_SHOW target, not checked), PoppetRenderScale +0x58.

### Microchip part: Reflect_PMicroChip 0x8164e68c (guess)
CircuitBoardThing +0xc, HideInPlayModeOld +0x18, WiresVisible +0x19, LastTouched +0x1c, Offset +0x20, CircuitBoardSizeX +0x3c, CircuitBoardSizeY +0x40, Name +0xa8, CompactComponents +0xb4.

### Poppet state header: Reflect_PoppetState 0x81673cf8
mode +0x14, submode +0x18: the MODE_* / SUBMODE_* pair (enums.txt). The offsets equal the fields the state constructors write (9x), so this reflects the state object itself.

### Cursor hit record: Reflect_PoppetHit 0x81673d90 (guess)
HitPoint_Fred +0x0, Normal +0x10 (vectors), BaryU +0x20, BaryV +0x24, TriIndex +0x28, HitThing +0x2c, HitPort +0x38, RefThing +0x3c, RefPort +0x48, OnCostumePiece +0x4c, DecorationIdx +0x50, SwitchConnector +0x54 (bool).
One record describes what the cursor is on: the triangle and barycentric position (sticker and decoration placement), the thing and port (wire connect, 0x81328388), and whether it is a costume piece.

### Emitted object record: Reflect_EmittedRef 0x81621980 (guess)
Creator +0x3c, PlanDescriptor +0x20, Emitter +0x60, Lifetime +0xc, AliveFrames +0x10, Flags +0x64.

Not named: 0x81647800 (Things +0x10) and 0x8165ba9c (Name +0x8, Things +0x18): thing lists, owner unknown.

## 9x. Poppet state class tree, from the constructors (dis.py read)
Root vtable 0x8183ab4c. Two constructors of it set the same header: +0x10 poppet, +0x14 MODE, +0x18 SUBMODE, +0x1c = 0.
- PoppetState 0x8183bf1c (34 slots): PoppetState_ctor 0x8113b90c(this, poppet, mode, submode). Menu and tweak states (late 20 list in NOTES).
- EditStateBase 0x8183bfac (36 slots): EditState_ctor 0x8113cee2(this, poppet, mode, submode), default 0x8113ce84. Adds zeroed fields +0x34..+0x50 and an object at +0x54. Children: DecorationStateBase 0x8185762c (mode 1), DecorationHoverState 0x818576d0 (mode 1, SUBMODE_PLACE_DECORATIONS 0x27), PickStateBase 0x8185b58c (mode 2 = MODE_CURSOR), PickState 0x8185b62c.
- EditToolBase 0x8183c044 (48 slots, child of EditStateBase): ToolState_ctor 0x8113d264(this, poppet, submode) always passes MODE_EDIT (1); default 0x8113d1d4; a third constructor 0x8113d2f8 reads the game object DAT_818e56ec. Fields: +0x88..+0xc4 zero, +0xac and +0xc8 = 1.0, +0xe4 = 0x1e, +0xe8 = 1.
  Children and the submode each one passes: PlaceJointTool 0x818570fc = SUBMODE_PLACE_BOLT (0x28), AttachJointTool 0x81857fb4 = SUBMODE_LONG_JOINT (0x29), PlaceObjectTool 0x81857a08 = SUBMODE_DECORATIVE_THING (0x2a), EditVertsTool 0x81857b98 = SUBMODE_EDIT_VERTS (6), EditUVTool 0x81858b80 = SUBMODE_EDIT_UV (0x2e), SelectionTool 0x81857ad0 (submode from its caller).
- CameraToolBase 0x81858a28: PoppetState_ctor with MODE_TWEAK_CUSTOM (5), ctor 0x8132c1b8. PopitMenuState 0x818581a0: MODE_MENU (3), submode 0.
- 0x81858878 (TweakStateBase, guess): no constructor of its own in the binary; its destructor 0x81728090 is also slot 0 of TweakModeState 0x81858908, so it is the folded base of the tweak states. Its one own method, slot 19 0x81328ef0 Tweak_GetSelectionBounds(this, centre out, half size out), walks the selection list of the poppet (pointer +0x144, count +0x148, 12 bytes per entry) and returns the box of all selected things; a thing with a script part can supply its own box (0x8139cab6, result type 5).

CLASSES.md is built by slot matching and shows EditToolBase and DecorationStateBase under PoppetState and the six tools as roots; the constructor reads above are the checked version.

So a tool is one class per SUBMODE, all sharing EditToolBase; the 48-slot table is the tool interface (update, draw, button prompts), and MODE says which family the state belongs to.

## 9y. Thing part mask (read, dump decomp_rthing.c)
Reflect_Thing 0x81664b50 tests one bit per part in the 64-bit mask at Thing +0x10 (low word +0x10, high word +0x14) and gets the part with Thing_GetPart 0x8122fe7c(mask address, part number).
- Bit n = part n in the order of 9w: 0 PBody, 1 PJoint, 2 PWorld, 3 PRenderMesh, 4 PPos, 5 PTrigger, 6 PYellowHead, 7 PAudioWorld, 8 PAnimation, 9 PGeneratedMesh, 0xa PLevelSettings, 0xb PSpriteLight, 0xc PScriptName, 0xd PCreature, 0xe PCheckpoint, 0xf PStickers, 0x10 PDecorations, 0x11 PScript, 0x12 PShape, 0x13 PEffector, 0x14 PEmitter, 0x15 PRef, 0x16 PMetaData, 0x17 PCostume, 0x18 PCameraTweak, 0x19 PSwitch, 0x1a PSwitchKey, 0x1b PGameplayData, 0x1c PEnemy, 0x1d PGroup, 0x1e PPhysicsTweak, 0x1f PNpc, 0x20 PSwitchInput, 0x21 PMicroChip, 0x22 PMaterialTweak, 0x23 PMaterialOverride, 0x24 PInstrument, 0x25 PSequencer, 0x26 PControlinator. Bits 0, 1, 2, 3, 0xb..0x1f, 0x20, 0x21, 0x25, 0x26 were read in the dump; the rest follow the same sequence of calls.
- Thing +0x34 points to a table of part pointers indexed by part number (0x81328ef0 reads PScript at table +0x44 = 0x11 * 4; 0x8113d2f8 reads PWorld at table +8).
- Bits above 0x26 exist at run time and are not saved: bit 0x28 (tested in 0x8113d2f8) and bit 0x32 (tested in 0x81328ef0). Their pointers sit in the thing itself at +0x38 + 4 * k, with k taken from 2-bit fields of the word at +0x18 (bits 2..3 for 0x28, bits 22..23 for 0x32). Which parts these are is not known.
So a tool asks what a thing is by testing mask bits: has PShape (0x12) = editable material, has PJoint (1) = connector, has PSwitch (0x19) = logic source.

## 9z. Mode 5 body writer (read, dump decomp_bodyw.c)
Resource_WriteBody 0x816ca078(stream, resource) is a switch on the resource type byte at +0x3c, one direct call per type, for types 1..55 (table: ghidra/rtype_body.txt). This is a second per-type table next to the thunk row of 9u, and it also covers the types above 30 that 9u could not reach. Type 31 returns 0x69, an unknown type returns 0x6d, types 46, 54 and 55 are written inline. The functions differ from the 9u row for the same type (mesh: 0x8167c8e8 here, 0x8167f730 there; level: 0x816d5a58 here, Reflect_Level 0x816d6180 there) and, by their call lists, do not call the 9u functions directly.
Level body read: Level_WriteBinary 0x816d5a58(stream, level) writes the fields of 9v as raw big-endian data, with no field names. Order: the block at +0x58 (0x81605f00), PlayerRecord +0x64 (0x816d59c0, 0x20 entries), a second 0x20-entry array at +0x4e4 (0x816d5928), the u32 at +0x564, then TutorialInventory as count +0x44 and 0x70-byte items from +0x40 (item writer 0x816b03e8), TutorialInventoryData as count +0x50 and 0x10-byte items from +0x4c (0x816acf90), then the byte TutorialInventoryActive +0x588; the tail was not read. The stream cursor is +0x68, its limit +0x6c, and 0x8100b54c grows it. So mode 5 is the compact binary form of the same data the reflect functions describe by name: every u32 is byte-swapped to big-endian, arrays are a count followed by the items.

Tail of Level_WriteBinary (read): byte TutorialInventoryActive +0x588, byte CopiedFromSomeoneElse +0x58b, u32 MusicGuid +0x574, u32 MusicSettingsGuid +0x578, then the 3 floats MusicStemVolumes +0x57c (0x8162e5c0, count 3). So the whole binary level body is the 9v field list in order, nothing extra. The reader with the same order is 0x816d5d60 Level_ReadBinary (it also reads the 0x10-byte items with 0x816acff8 and resizes the array at +0x4c with 0x815c4be0).

## 9za. Download job map (read, dump decomp_sv2.c; corrected in 9ze: these are level download jobs, not editor saves)
The download jobs live in a std::map keyed by a 64-bit id (two u32, compared high word first); the value is a counted reference to a DownloadJob (0xe0 bytes, vtable 0x8183b134, constructor 0x8105885a). Tree nodes: +0 left, +4 parent, +8 right, +0xc key, +0x14 job reference, +0x19 nil flag.
- 0x810589fc DownloadJobMap_GetOrCreate(out ref, map, key, arg): equal_range on the key. Found: returns a new reference to the existing job, so one slot never has two download jobs. Not found: operator new(0xe0), DownloadJob constructor, insert, one DownloadJob_Step (0x810587da) at once, return the reference. Callers: Download_Start 0x8105a062 and Download_UpdateAll 0x8105a1ce (9ze).
- 0x81058c8e DownloadJobMap_Update(mgr): once per frame from 0x81050226. Steps every job; a job that reports finished is erased from the map (0x81577858). Finished with state (+0x28) 3 = success: mgr +0x10 += the two sizes at job +8 -> +0x40 -> +0xd4 and +0xd8 (bytes written, guess). State 2 = failure: mgr +0x14 = 1. Ends with 0x81057592 on DAT_818d2328.

## 9zb. Thing object type and the board-hidden byte (read, dumps decomp_thing.c, decomp_sreq2.c)
- Thing +0x7e is the object type: one byte indexing the OBJECT_ name table 0x818266e8 (157 names in enums.txt: 0 OBJECT_UNKNOWN, 1 OBJECT_TAG, 2 OBJECT_WORLD, 3 OBJECT_MICROCHIP, 6 OBJECT_CONTROLINATOR, 7 OBJECT_MOVINATOR, 0x24 OBJECT_CAMERA_MOVIE, 0x40 OBJECT_SWITCH_CIRCUIT_BOARD, 0x43 OBJECT_LETHALISER, 0x84 OBJECT_POWERUP_MOVE, 0x95 OBJECT_CURSOR). Every "kind byte +0x7e" in the sections above is this enum.
- Thing +0x7f = hidden on a closed circuit board (meaning inferred: the change is applied through a fade, 0x810fd988, target 1.0 when the byte clears and 0 when it sets). 0x8122ab62 Thing_UpdateBoardHidden(thing, a, b) computes it:
  - a thing with no +0x5c gets 0;
  - OBJECT_MICROCHIP / OBJECT_CURSOR: 1 when the list at +0x60 has an entry [4] whose +0xc is 0 (board closed);
  - OBJECT_SWITCH_CIRCUIT_BOARD: inherits the byte of a parent of type microchip, controlinator, movinator or cursor;
  - a child of a circuit board also inherits, and gets 1 when its grid cell (0x810b6e6a, cell size 1 / 52.5 of the board value from 0x810bbd94) falls outside the board;
  - OBJECT_CAMERA_MOVIE that stays visible is registered at world +0x5b4 (0x8141b0b2).
  On a change it calls the setter 0x8122ab00 Thing_SetBoardHidden, then repeats for the thing in its microchip part (+0xc) and every child of that (+0x48 first, +0x4c next).
- 0x8118128c Game_RequestSaveLevel(game, flag) (guess): with game +0x80 set, or the slot id at game +0x19c / +0x1a0 equal to DAT_818d2430 / DAT_818d2434, it builds a type 9 resource descriptor from the level at game +0x84 (hash at +0x20, else guid at +0xc) and posts it (0x8105c914, queue DAT_819077c0); otherwise it sends the slot id at +0x1ac / +0x1b0 to 0x812df5c0.
- 0x811813e8 Game_CloneLevelBySave (guess): in create mode (game +0x3a9, level byte +0x3d of 4 or 5, flag 0x40 at +0x3f of the second level from 0x8114c27e) it makes a new level resource (0x590 bytes, 0x81186cba), saves the current level into a buffer (Level_SaveResource) and loads that buffer into the new one (Level_LoadResource). The copy is passed to 0x811913c2. A level is duplicated by serialising it, the same way undo snapshots work (9k).

## 9zc. Plan binary body (read, dump decomp_plan5.c)
A plan (RTYPE_PLAN, type 38: one saved object, sticker or costume piece) is written by 0x816d6774 Plan_WriteBinary(stream, plan), all big-endian:
1. u32 plan +0x50 (revision of the thing data);
2. u32 byte count (+0x60), then that many raw bytes from +0x5c: the serialised things of the object, kept as an opaque blob;
3. the inventory details record at +0x68 (0x816aaf8c InventoryDetails_WriteBinary; body not read);
4. u32 +0xb4 and u32 +0xb8 (not identified).
The reader 0x816d6834 Plan_ReadBinary takes the same order. It adds each blob size to a running total in the stream (+0x40, 64-bit) and returns error 0x67 once the total reaches 50000000 bytes. After a read it stamps the plan as current: +0x50 = 0x3e2 (the revision this build writes), +0x54 = 0x44310084 (branch tag), +0x58 = the stream flag byte +0x2c.
So placing an object from the Popit means deserialising the blob of its plan into the level, and capturing an object means serialising its things into a new blob (the commit paths in 9g / 9m call into this).

Inventory details record (dump decomp_invd.c; callee list read, field order not checked one by one): 0x816aaf8c writes the struct that FIELDS.md lists under 0x816ac304: DateAdded +0 (64-bit, 0x8100bea8), LevelUnlockSlotID +8, HighlightSound +0x10, Colour +0x14, Type +0x18, SubType +0x1c, the two translation tags +0x20 / +0x24, a creator id at +0x28 (0x816aaf34), Icon +0x2c (resource descriptor, 0x816aae50), UserCreatedDetails +0x30 (two UTF-16 strings, each a count then count * 2 bytes), PhotoData +0x34 (0x81611060) and EyetoyData +0x38 (0x816139c4), each written only when present, the u16 indices LocationIndex / CategoryIndex / PrimaryIndex +0x40..+0x44, a record at +0x3c (0x816aadf8) and the bytes ToolType +0x46, Flags +0x47, MakeSizeProportional +0x48. This is what the Popit shows for an item: name, description, icon, category and creator all travel inside the plan.

## 9zd. Text keys and the Move save check (read, tool tools/lamskey.py)
- Text is looked up by a 32-bit hash of its key name: 0x8123b858 Text_LookupKey(hash, out string), non-zero when found. The hash walks the first 32 characters backwards (v = v * 0x1b + char, short keys padded with spaces), a second pass does characters 33..64 when the key is longer (else the constant 0xC8509800), result = v0 + v1 * 0xDEADBEEF, low 32 bits. The key names themselves are still in the eboot as plain strings, so tools/lamskey.py hashes every identifier string (26682 keys, ghidra/work/lamskeys.tsv) and resolves the constants in the dumps: all 106 Text_LookupKey constants in the current dumps resolve (ghidra/work/textkeys.txt).
- Game_PreSaveCheck 0x81183706 (section 7): the three keys are SAVE_MESSAGE_MOVE_FLAG_NOT_SET, TG_Yes, TG_No. So the level byte at world +0x60 is the "needs PlayStation Move" flag of the level, and the check is: the level holds an OBJECT_MOVINATOR or OBJECT_POWERUP_MOVE but the flag is off -> ask Yes / No (dialog 0x62 or 0x63) and do not save yet. It is a question, not a hard block; what Yes does is in the dialog handlers (not read).
- Limits shown by the editor, by key: LIMIT_CANNOT_SAVE (0x812fae18), LIMIT_EMITTERS_FAILING (0x812fb04a), LIMIT_TOO_COMPLICATED (0x81348814), LIMIT_APPROACHING (thermometer 0x812f9db0), LIMIT_TOO_MANY_STICKERS (sticker paint 0x8121a488), LIMIT_TOO_MANY_DECORATIONS (decoration attach 0x814212fe), TG_STICKERING_RESTRICTED (0x813519a6).
- Paint tool prompts: POPPET_SAVE_PAINTING_REQUEST (0x81320130), PAINT_QUIT_CHECK (0x8132124e), PAINT_MESSAGE_NO_MOVE_CONTROLLER (0x81330dcc), default item name ITEM_NAME_DEFAULT_PAINTING (0x8131f0c8).
- 0x81331038 is the shared text entry opener: its title key is one of NOTE_ENTER_TEXT, SPEECH_BUBBLE_ENTER_SPEECH, POPPET_TEXT_ENTRY_ITEM_NAME, SEQUENCER_NAME, TWEAK_CONTROLINATOR_BUTTON_PROMPT_NAME and others (which case picks which: not read).

## 9ze. The job map is the level download manager (read; tool tools/blscan.py)
The only callers of the 9za functions are script natives (found by scanning every bl / b.w target with tools/blscan.py), and their names settle what the map is:
- native_StartDownload 0x811f548a -> 0x8105a062 Download_Start(slot id): DownloadJobMap_GetOrCreate for that slot with the current profile (0x8114cb44).
- native_UpdateAll 0x811f54c2 -> 0x8105a1ce Download_UpdateAll: copies the slot map of the profile (profile +0x98, nodes of 0x1e8 bytes, slot record at node +0x18) and starts a job for every slot whose status (0x810594c0, flag 1) is 1.
- native_IsLevelDownloading 0x811f5462 -> 0x8105a018: job found (DownloadJobMap_Find 0x810595fc) and state +0x28 not 3.
- native_AreDownloadsInProgress 0x811f54ae -> 0x8105a148: any job with state 1.
- native_CancelDownloads 0x811f54ba -> 0x8105a198 -> 0x81059c5a DownloadJobMap_CancelAll: every job in state 1 without the byte +0x44 drops its pending work (+0x3c) and goes to state 2 with code 4 at +0x2c.
- native_NeedsUpdate 0x811f54ca -> 0x8105a10a -> 0x81059a9c; native_RemoveDownload 0x811f54f2 -> 0x8105a0b8 -> lbp_DeleteOldestFartsAsync 0x81059302.
- Job state +0x28: 1 running, 2 failed or cancelled, 3 done. The step (0x810587da) waits for every dependency, then calls lbp_SaveLevelFart (9o) to store the downloaded level locally. So lbp_SaveLevelFart is the cache write of a downloaded level; the editor save goes through Game_PreSaveCheck (section 7, 9zd) and message 0x37.
- 0x810594c0 Download_SlotStatus(profile, slot, deep): slot type field (+0x100) must be 0x1d with the top bit set, else 4; with deep it takes the worst status of the linked slots; a queued resource in state 1 gives 2, state 3 gives 4; no local copy gives 3; a local copy with the same hash gives 0. Exact meaning of each value: not read.

## 9zf. Where the edited level is written (read, dumps decomp_sv3.c, decomp_sv4.c, decomp_sv5.c; tool tools/keyscan.py)
- tools/keyscan.py lists every text key hash loaded as a constant in the code (movw + movt): 1535 uses in 279 functions, ghidra/work/keyuse.tsv. The save game texts (SAVEGAME_ERROR_NO_SPACE_QUICKSAVE, SAVEGAME_FAIL_UNKNOWN_ERROR, MSG_PROCEED_WITHOUT_SAVING) sit in 0x814a2416 and 0x814a395e, next to two callers of the level serialiser.
- 0x814a2a02 SaveGame_SerialiseProfile(job): first step of a profile save. With a game object present it calls Game_CloneLevelBySave (9zb), so the level being edited is copied by serialising it and handed to the profile (0x811913c2). Then it calls the pre-save hook of the profile resource (job +0x20, vtable +0x38), serialises that resource into the buffer at job +0x54 (hash record to +0xac), calls the post-save hook (vtable +0x3c, argument = success) and sets the byte +0x119. With job +0x100 = 1 it first copies the slot map of the profile (+0x8c) into job +0x60. Caller 0x814a2b7e.
- 0x814a2ce2 (3184 bytes, read in part) is the writer that follows: it also calls the serialiser and builds file names "moon%u_%u".
- So the save order for an edited level is: Game_PreSaveCheck (limits and Move flag, 9zd) -> message 0x37 -> level cloned into the profile by serialising -> profile save job writes the files. The handler of message 0x37 itself was not located; this chain is from the callers of the serialiser.
- Not the save: 0x8123409e (state 3 at +0xf0: saves the resources of a flagged thing list, queues 0x34-byte records, replaces two undo snapshots by one; caller 0x8123dcf2) and 0x8146b6f4 (makes a new 0x590 level resource and loads a serialised copy, like Game_CloneLevelBySave). Meaning of both: not read.
- Leaving create mode with changes: 0x812c68c4 asks CREATE_MODE_LEAVE_TO_POD_PROMPT with CREATE_MODE_LEAVE_SAVE / CREATE_MODE_LEAVE_DISCARD / TG_Cancel.

## 9zg. Save job: serialise step and file writer (read in part, dumps decomp_sv5.c, decomp_sv6.c, decomp_sv7.c)
- 0x814a2b7e SaveJob_RunSerialise(job): the step before the write. The job result code is job +0x104: 3 = the user of the job (job +0xc) is not the current one, 2 = the resource (job +0x20, taken only when its type byte +0x3c is 0x20) has the byte +0x4ec set (it then sets bit 2 of +0x3f on the resource and its owner), 5 = SaveGame_SerialiseProfile failed. On success it copies resource +0x370 to job +0x38 and calls 0x81383706 SaveJob_StartWorker (stamps the time at job +0x18, sets job +8 = 1, starts the worker 0x81367790 through the pool DAT_818613e0).
- It skips the save while a create-mode object of the level is still held (path through 0x8117b8c8 / 0x81177112 / 0x8113adb2 returning non-zero) unless resource +0x388 is 0x80000001. Meaning of that test: not read.
- 0x814a2ce2 SaveJob_WriteAndVerify(job): lists the save folder (0x8123e2d6 = folder of a slot), deletes stale "moon%u_%u" files (name builder 0x81164cce), writes with 0x81382c9e SaveFile_Write (open mode 3, seek, sync, close), reads back with 0x81382a36 SaveFile_ReadBack and compares the hashes with memcmp; a mismatch removes the file. It ends with the "littlefart" calls 0x810425fa. The moon files are the levels on the player moon, written one file per slot. Order of the steps inside: not fully read.
- 212 more functions got Text_<key> names from tools/keyscan.py output (hand.txt lines tagged textkey_late40): the name says which text key the function loads, not what it does.
- The job class (late 41): its vtable sits at file offset 0x85d5f4 of eboot.elf, followed by the string "QuickSaveProfile"; slot +0x10 is 0x817621b8 (auto name QuickSaveBigProfile). Slots: +8 = SaveJob_WriteAndVerify (the worker entry 0x81367790 only calls vtable +8), +0xc = 0x814a395e QuickSaveJob_Finish (holds the SAVEGAME_ERROR texts; RunSerialise calls it after setting an error code), +0x2c = SaveJob_RunSerialise. So the edited level reaches the disk through the quick save of the big profile.

## 9zh. Network message path for SAVE_LEVEL (0x37) (read in part, disassembly + dumps decomp_svb.c, decomp_svc.c)
- Correction to 9zb: 0x812c2896 is not a message builder. It only acts for r1 = 8, 0xa or 0xc (calls 0x812c048c on session +0x1804); for 0x37 it does nothing. The message is the record on the stack of Game_SendSaveLevelMsg (type 0x37 at +0, session +0x1abc at +4) sent by 0x812c27f8 Net_SendMessage.
- Net_SendMessage picks a channel by type: 7 for 0x5f..0x60, 5 for 0x11..0x14 and 0x61, else 3 (so 3 for SAVE_LEVEL), gets a buffer with 0x812cad50 and appends with 0x812dc746; a buffer over 0x100000 bytes is dropped (0x812cb66c).
- Receive side: 0x812acb38 Net_OnMessage switches on the type (0..0x61, table at 0x812acbca, 24 distinct targets). SAVE_LEVEL has no case of its own: the default 0x812ad4c4 calls 0x812af118 Net_RouteGameMessage, which switches on the delivery kind (message +4, 0..0x14) and calls 0x812af092 Net_BufferGameMessage. That one appends the bytes to the buffer of the sending peer (same 0x812cad50 / 0x812dc746 pair).
- So game messages such as SAVE_LEVEL are not handled in the network callback: they are queued per peer and read later. The reader of that queue (and with it the code that starts the quick save job of 9zg) was not located.
- Other switches on values that include 0x37 are not message code: Poppet_HandleMessage 0x812fcb1a (0..0x57, default for 0x36..0x38) and the poppet functions 0x81134e52 / 0x8113735a / 0x8113208e (tool mode 0x37 / 0x38).

## 9zi. Who starts the quick save job (read, dump decomp_svh.c; tool tools/mvscan.py)
- The job vtable object is at 0x8185d56c (vptr = +8 = 0x8185d574). tools/mvscan.py finds the code that loads an address with movw + movt: the constructor is 0x814a28f6 QuickSaveJob_ctor (job size 0x120).
- Its only caller is 0x81383816 SaveQueue_AddQuickSave(queue, profile ref, user, mask, mask2, flag, doProfile, doBigProfile). It makes a job only when the dirty byte +0x3f of the resource has no bit 4 and has a bit of mask (or of mask2 when bit 8 is set). It can make two jobs: one for the profile and one for the object returned by 0x81188d38 (the big profile, which holds the moon levels). Jobs are queued with 0x8138378e.
- Callers of SaveQueue_AddQuickSave: 0x81383c46 and 0x81383cd4 (not read).
- So a save is not started by a direct call from the editor: code marks the profile dirty (byte +0x3f; SaveJob_RunSerialise sets bit 2 there when it has to retry) and the save queue turns dirty profiles into quick save jobs. What sets the dirty bit after message SAVE_LEVEL: not located.

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
- The rest of decomp_joint.c.
- Body writer 0x816ca078, reflect functions of types above 30, handler of network message 0x37 (the real save). The Yes / No handlers of the Move flag dialog 0x62 / 0x63 (9zd).
- Class trees are in CLASSES.md (Poppet tool states sit under PickState 0x8185b62c; each constructor passes its SUBMODE number). Unnamed classes there still need reading.
- Libraries: FMOD, zlib and libpng are named; vorbis, Bink and xml are not. libult and steroid suprx modules.
