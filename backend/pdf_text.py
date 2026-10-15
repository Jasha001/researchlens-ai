"""Read horizontal text blocks column-by-column; retain page numbers."""
def extract_page(page):
    width=page.rect.width
    blocks=[]
    marginal=[]
    for b in page.get_text('dict')['blocks']:
        if b.get('type')!=0: continue
        lines=[]
        for line in b.get('lines',[]):
            text=''.join(s['text'] for s in line.get('spans',[]))
            if abs(line.get('dir',(1,0))[1])>.2:
                marginal.append(text);continue
            lines.append(text)
        text='\n'.join(lines).strip()
        if text: blocks.append((*b['bbox'],text))
    left=[b for b in blocks if b[0]<width*.5 and b[2]<width*.52]
    right=[b for b in blocks if b[0]>=width*.48]
    if len(left)>=3 and len(right)>=3:
        wide=[b for b in blocks if b not in left and b not in right]
        # Full-width titles precede the two-column body in typical papers.
        ordered=sorted(wide,key=lambda b:b[1])+sorted(left,key=lambda b:b[1])+sorted(right,key=lambda b:b[1])
    else: ordered=sorted(blocks,key=lambda b:(b[1],b[0]))
    return '\n\n'.join(b[4] for b in ordered)+('\n\n'+'\n'.join(marginal) if marginal else '')
