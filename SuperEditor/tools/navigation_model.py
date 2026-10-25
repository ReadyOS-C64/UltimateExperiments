"""Host-only source row oracle, independent of assembled navigation/index code."""
import bisect

BODY_ROWS=22
PAGE_ROWS=21

def visual_rows(data,width=40):
    result=[];start=pos=col=0
    for value in data:
        if value==13:
            result.append((start,pos));pos+=1;start=pos;col=0
        else:
            pos+=1;col+=1
            if col==width:
                result.append((start,pos-1));start=pos;col=0
    result.append((start,len(data)))
    return result

def move(command,data,caret,preferred=None,layout=None):
    if command in (36,37,38,39):
        layout=visual_rows(data) if layout is None else layout
        index=bisect.bisect_right([start for start,end in layout],caret)-1
        if preferred is None:preferred=caret-layout[index][0]
        target=index+{36:-1,37:1,38:-PAGE_ROWS,39:PAGE_ROWS}[command]
        if target<0:return 0,preferred
        if target>=len(layout):return len(data),preferred
        start,end=layout[target]
        return start+min(preferred,end-start),preferred
    start=data.rfind(b'\r',0,caret)+1
    end=data.find(b'\r',caret);end=len(data) if end<0 else end
    return {32:start,33:end,34:0,35:len(data),40:max(start,caret-40),41:min(end,caret+40)}[command],None
