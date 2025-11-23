# ---------------------------------------------------------------------------
# Pulmageneraattori example: python cbgenerate.py 80 6 20
# 80 pulmien määrä,  6 alaraja ja 20 yläraja siirroille
# ---------------------------------------------------------------------------

import json
import random
import sys
from collections import deque

BOARD = 5

# ---------------------------------------------------------------------------
# PALIKAT (pelin mukaiset)
# ---------------------------------------------------------------------------

BASE_PIECES = [
    {
        "id": "P1",
        "pattern": [
            ['X', 'B'],
            ['O', 'X'],
            ['O', 'X']
        ]
    },
    {
        "id": "P2",
        "pattern": [
            ['O', 'X'],
            ['X', 'B'],
            ['O', 'X']
        ]
    },
    {
        "id": "P3",
        "pattern": [
            ['O', 'X'],
            ['O', 'B'],
            ['X', 'X']
        ]
    },
    {
        "id": "P4",
        "pattern": [
            ['O', 'X'],
            ['B', 'X'],
            ['O', 'X', 'B']
        ]
    }
]

# ---------------------------------------------------------------------------
# Palikoiden orientaatiot ja normalisointi
# ---------------------------------------------------------------------------

def build_cells_from_pattern(pattern):
    cells=[]
    for y,row in enumerate(pattern):
        for x,ch in enumerate(row):
            if ch in ("X","B"):
                cells.append((x,y,ch))
    minx=min(c[0] for c in cells)
    miny=min(c[1] for c in cells)
    return [(x-minx,y-miny,c) for (x,y,c) in cells]

def rot90(cells):
    out=[(c[1], -c[0], c[2]) for c in cells]
    minx=min(c[0] for c in out)
    miny=min(c[1] for c in out)
    return [(x-minx,y-miny,c) for (x,y,c) in out]

def build_variants(cells):
    v0=cells; v1=rot90(v0); v2=rot90(v1); v3=rot90(v2)
    uniq=[]; seen=set()
    for v in (v0,v1,v2,v3):
        key=tuple(sorted(v))
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    return uniq

PIECES = {}
for b in BASE_PIECES:
    base=build_cells_from_pattern(b["pattern"])
    PIECES[b["id"]] = build_variants(base)

# ---------------------------------------------------------------------------
# Precompute kaikki mahdolliset sijoitukset jokaiselle palikalle
# ---------------------------------------------------------------------------

PLACEMENTS = {pid: [] for pid in PIECES.keys()}

for pid, variants in PIECES.items():
    for ori_idx, v in enumerate(variants):
        maxdx=max(c[0] for c in v)
        maxdy=max(c[1] for c in v)
        for ax in range(BOARD-maxdx):
            for ay in range(BOARD-maxdy):
                cells=[]
                ok=True
                for dx,dy,kind in v:
                    x=ax+dx; y=ay+dy
                    if not (0<=x<BOARD and 0<=y<BOARD):
                        ok=False; break
                    cells.append((x,y,kind))
                if ok:
                    PLACEMENTS[pid].append({
                        "ori": ori_idx,
                        "ax": ax,
                        "ay": ay,
                        "cells": cells
                    })

# ---------------------------------------------------------------------------
# Goal-tila: palikat ensin + kissat B-ruutuihin
# ---------------------------------------------------------------------------

def generate_random_goal_state():
    """Asettaa palikat laudalle laillisesti ja palauttaa goal_state + kissat."""
    while True:
        occ=[[None]*BOARD for _ in range(BOARD)]
        state={}
        ok_global=True

        # Sijoitusjärjestys tärkeä (P4 ensin)
        for pid in ["P4","P3","P2","P1"]:
            cands=PLACEMENTS[pid][:]
            random.shuffle(cands)
            placed=False

            for pl in cands:
                conflict=False
                for x,y,kind in pl["cells"]:
                    if occ[y][x] is not None:
                        conflict=True; break
                if conflict: continue

                state[pid]=(pl["ori"],pl["ax"],pl["ay"])
                for x,y,kind in pl["cells"]:
                    occ[y][x]=(pid,kind)
                placed=True
                break

            if not placed:
                ok_global=False
                break

        if not ok_global:
            continue

        cats=[]
        for y in range(BOARD):
            for x in range(BOARD):
                cell=occ[y][x]
                if cell and cell[1]=="B":
                    cats.append((x,y))

        if len(cats)!=5:
            continue

        return state, cats

# ---------------------------------------------------------------------------
# Laudan tarkistus + liikkeet
# ---------------------------------------------------------------------------

def occupancy_from_state(state):
    occ=[[None]*BOARD for _ in range(BOARD)]
    for pid,(ori,ax,ay) in state.items():
        cells=PIECES[pid][ori]
        for dx,dy,k in cells:
            x=ax+dx; y=ay+dy
            if not (0<=x<BOARD and 0<=y<BOARD):
                return None
            if occ[y][x] is not None:
                return None
            occ[y][x]=(pid,k)
    return occ

def all_cats_free(state,cats):
    occ=occupancy_from_state(state)
    if not occ: return False
    for (cx,cy) in cats:
        cell=occ[cy][cx]
        if cell and cell[1]=="B":
            return False
    return True

def legal_moves(state,cats):
    moves=[]
    for pid in PIECES:
        o_ori,o_ax,o_ay=state[pid]
        for ori,v in enumerate(PIECES[pid]):
            maxdx=max(c[0] for c in v)
            maxdy=max(c[1] for c in v)
            for ax in range(BOARD-maxdx):
                for ay in range(BOARD-maxdy):

                    if (ori,ax,ay)==(o_ori,o_ax,o_ay):
                        continue

                    new=dict(state)
                    new[pid]=(ori,ax,ay)

                    occ=occupancy_from_state(new)
                    if not occ:
                        continue

                    # tile ei saa peittää kissaa
                    blocked=False
                    for (cx,cy) in cats:
                        cell=occ[cy][cx]
                        if cell and cell[1]=="X":
                            blocked=True; break
                    if blocked:
                        continue

                    moves.append(new)
    return moves

# ---------------------------------------------------------------------------
# BFS: goal → alku
# ---------------------------------------------------------------------------

def backward_bfs(goal,cats,maxdepth):
    def key(st):
        return tuple(sorted((pid,*vals) for pid,vals in st.items()))

    q=deque([goal])
    dist={key(goal):0}

    while q:
        cur=q.popleft()
        d=dist[key(cur)]

        if all_cats_free(cur,cats) and d>0:
            return cur,d

        if d>=maxdepth:
            continue

        for nxt in legal_moves(cur,cats):
            k=key(nxt)
            if k not in dist:
                dist[k]=d+1
                q.append(nxt)

    return None,None

# ---------------------------------------------------------------------------
# Duplikaattiavain
# ---------------------------------------------------------------------------

def canonical_key(cats, state):
    cats_part=tuple(sorted(cats))
    pieces_part=tuple(sorted((pid,vals[0],vals[1],vals[2]) for pid,vals in state.items()))
    return (cats_part,pieces_part)

# ---------------------------------------------------------------------------
# Yhden pulman generointi
# ---------------------------------------------------------------------------

def generate_puzzle_once(maxdepth,minmoves,maxmoves):
    goal,cats = generate_random_goal_state()
    start,moves = backward_bfs(goal,cats,maxdepth=maxdepth)
    if not start:
        return None
    if not (minmoves <= moves <= maxmoves):
        return None
    return moves,cats,start

# ---------------------------------------------------------------------------
# Pääohjelma: massagenerointi
# ---------------------------------------------------------------------------

def main():
    # parametrit
    if len(sys.argv)>=2:
        count=int(sys.argv[1])
    else:
        count=60

    if len(sys.argv)>=3:
        minmoves=int(sys.argv[2])
    else:
        minmoves=1

    if len(sys.argv)>=4:
        maxmoves=int(sys.argv[3])
    else:
        maxmoves=30

    print(f"Luodaan {count} pulmaa siirtoalueella {minmoves}–{maxmoves}...")

    maxdepth=30
    seen=set()
    puzzles=[]

    attempts=0

    while len(puzzles) < count:
        attempts+=1
        res = generate_puzzle_once(maxdepth,minmoves,maxmoves)
        if not res:
            continue

        moves,cats,start_state = res
        key = canonical_key(cats,start_state)
        if key in seen:
            continue
        seen.add(key)

        puzzle={
            "id":0,
            "name":str(moves),
            "cats":[{"x":x,"y":y} for (x,y) in cats],
            "pieces":[
                {"id":pid,"x":vals[1],"y":vals[2],"ori":vals[0]}
                for pid,vals in start_state.items()
            ]
        }

        puzzles.append((moves,puzzle))
        print(f"Pulma {len(puzzles)}/{count} (siirrot {moves}, yrityksiä {attempts})")
        attempts=0

    puzzles.sort(key=lambda x: x[0])

    out=[]
    for idx,(moves,p) in enumerate(puzzles,start=1):
        p["id"]=idx
        out.append(p)

    with open("cats_boxes_puzzles.json","w",encoding="utf-8") as f:
        json.dump(out,f,indent=2,ensure_ascii=False)

    print("\nValmis! Tiedosto cats_boxes_puzzles.json luotu.")

if __name__=="__main__":
    main()
