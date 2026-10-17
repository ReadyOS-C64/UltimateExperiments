
/* Native logical importer: a separate read-only rawfile callback, REU cached
 * FAT/ownership/traversal, bounded BFS and original byte sources at emission. */
#define EX_FAT (NF_META+0x20000UL)
#define EX_OWN (NF_META+0x25000UL)
#define EX_DIR (NF_META+0x26000UL)
#define EX_SEEN (NF_META+0x28000UL)
#define EX_DIR_BYTES 84U
nf_u16 nf_debug_dir,nf_debug_entry,nf_debug_cluster;nf_u8 nf_debug_stage;
static nf_u32 ex_bytes,ex_data,ex_root;
static nf_u16 ex_clusters,ex_spf,ex_roots,ex_dirs,ex_seen;
static nf_u8 ex_width,ex_spc,ex_valid,ex_label;
static nf_u8 ex_raw[32],ex_record[84],ex_seen_record[13];
static char ex_path[80];
static nf_u16 ex_parent,ex_first,ex_parent_first;
static void existing_reset(void){ex_valid=0;}

static nf_u8 ex_read(nf_u32 offset,void*buffer,nf_u16 length) {
    if(check())return nf_error;
    if(offset>ex_bytes||length>ex_bytes-offset)return fail(NF_E_SOURCE);
    if(nf_disk_read(offset,buffer,length)!=length)return fail(NF_E_IO);
    return 0;
}
static nf_u16 ex_fat(nf_u16 c) {
    nf_u32 at;nf_u16 value;
    at=ex_width==16?(nf_u32)c*2UL:(nf_u32)c*3UL/2UL;
    if(read_at(EX_FAT+at,pair,2))return 0;
    value=rd16(pair);return ex_width==16?value:(c&1?value>>4:value&0xfff);
}
static nf_u8 ex_eoc(nf_u16 c){return c>=(ex_width==16?0xfff8U:0xff8U);}
static nf_u8 ex_mark(nf_u16 c) {
    nf_u32 at;nf_u8 value,mask;
    if(c<2||c>ex_clusters+1U)return fail(NF_E_SOURCE);
    at=EX_OWN+c/8;mask=(nf_u8)(1U<<(c&7));
    if(read_at(at,&value,1))return nf_error;
    if(value&mask)return fail(NF_E_SOURCE);
    value|=mask;return write_at(at,&value,1);
}
static nf_u8 ex_owned(nf_u16 c){
    nf_u32 at;nf_u8 value,mask;at=EX_OWN+c/8;
    if(read_at(at,&value,1))return 0;
    mask=(nf_u8)(1U<<(c&7));
    return value&mask;
}
static nf_u8 ex_chain(nf_u16 first,nf_u32 size,nf_u8 directory) {
    nf_u16 c,count,expected;
    if(!directory&&!size)return first?fail(NF_E_SOURCE):0;
    if(size>ex_bytes||first<2)return fail(NF_E_SOURCE);
    expected=(nf_u16)((size+(nf_u32)ex_spc*512UL-1UL)/((nf_u32)ex_spc*512UL));
    c=first;count=0;
    while(!ex_eoc(c)){
        if(count>=ex_clusters||ex_mark(c))return fail(NF_E_SOURCE);
        count++;c=ex_fat(c);if(nf_error)return nf_error;
        if(!directory&&count>expected)return fail(NF_E_SOURCE);
    }
    if(!count||(!directory&&count!=expected))return fail(NF_E_SOURCE);
    return 0;
}
static nf_u8 ex_duplicate(nf_u16 parent) {
    nf_u16 i;
    for(i=0;i<ex_seen;i++){
        if(read_at(EX_SEEN+(nf_u32)i*13UL,ex_seen_record,13))return nf_error;
        if(rd16(ex_seen_record)==parent&&!memcmp(ex_seen_record+2,ex_raw,11))return fail(NF_E_SOURCE);
    }
    if(ex_seen>=NF_MAX_FILES)return fail(NF_E_FULL);
    wr16(ex_seen_record,parent);memcpy(ex_seen_record+2,ex_raw,11);
    if(write_at(EX_SEEN+(nf_u32)ex_seen*13UL,ex_seen_record,13))return nf_error;
    ex_seen++;return 0;
}
static nf_u8 ex_name(void) {
    nf_u8 i,space,n;
    space=0;n=0;
    for(i=0;i<11;i++){
        if(i==8)space=0;
        if(ex_raw[i]==' '){space=1;continue;}
        if(space||!validchar(ex_raw[i]))return fail(NF_E_SOURCE);
    }
    if(ex_raw[0]==' ')return fail(NF_E_SOURCE);
    for(i=0;i<8&&ex_raw[i]!=' ';i++)import_name[n++]=(char)ex_raw[i];
    if(ex_raw[8]!=' '){import_name[n++]='.';for(i=8;i<11&&ex_raw[i]!=' ';i++)import_name[n++]=(char)ex_raw[i];}
    import_name[n]=0;
    if(strlen(ex_path)+n+(ex_path[0]?1U:0U)>=80U)return fail(NF_E_FULL);
    strcpy(import_path,ex_path);if(ex_path[0])strcat(import_path,"/");strcat(import_path,import_name);
    return 0;
}
static nf_u8 ex_save_dir(nf_u16 id,nf_u16 first,nf_u16 parent) {
    memset(ex_record,0,sizeof(ex_record));strcpy((char*)ex_record,import_path);
    wr16(ex_record+80,first);wr16(ex_record+82,parent);
    return write_at(EX_DIR+(nf_u32)id*EX_DIR_BYTES,ex_record,EX_DIR_BYTES);
}
static nf_u8 ex_add(nf_u16 id) {
    nf_u16 first,slot,child;nf_u32 size;nf_u8 attr,i;
    attr=ex_raw[11];first=rd16(ex_raw+26);size=rd32(ex_raw+28);
    if(attr&0xc0||attr==0x0f||(attr&0x18)==0x18)return fail(NF_E_SOURCE);
    if(ex_duplicate(id))return nf_error;
    if(attr&8){
        if(id||first||size||ex_label)return fail(NF_E_SOURCE);ex_label=1;
        for(i=0;i<11;i++)if(ex_raw[i]<32||ex_raw[i]>126)return fail(NF_E_SOURCE);
        memcpy(namebuf,ex_raw,11);if(lookup(0))return nf_error;
        if(found!=0xffff||new_entry(0))return fail(NF_E_SOURCE);
        ent.attr=attr;ent.kind=4;ent.time=rd16(ex_raw+22);ent.date=rd16(ex_raw+24);
        return putent(found);
    }
    if(ex_name())return nf_error;
    if(attr&0x10){
        if(size||ex_dirs>=NF_MAX_DIRS||ex_chain(first,0,1))return fail(NF_E_SOURCE);
        if(resolve(import_path)||lookup(target_parent))return nf_error;
        if(found!=0xffff)return fail(NF_E_SOURCE);
        child=nf_dir_count++;if(child>=NF_MAX_DIRS)return fail(NF_E_FULL);
        if(new_entry(target_parent))return nf_error;slot=found;
        ent.attr=attr;ent.kind=2;ent.source=(nf_u8)child;
        ent.time=rd16(ex_raw+22);ent.date=rd16(ex_raw+24);
        if(putent(slot))return nf_error;
        memset(&dir,0,sizeof(dir));dir.parent=target_parent;dir.entry=slot;
        if(putdir(child)||ex_save_dir(ex_dirs,first,id))return nf_error;
        ex_dirs++;return 0;
    }
    if(ex_chain(first,size,0)||start_put(import_path,0))return nf_error;
    ent.attr=attr;ent.time=rd16(ex_raw+22);ent.date=rd16(ex_raw+24);ent.size=size;
    ent.first=first;ent.kind=3;ent.source=0;return putent(found);
}
static nf_u8 ex_scan(nf_u16 id) {
    nf_u32 offset;nf_u16 cluster,index,count,slot,parent;nf_u8 end;
    if(read_at(EX_DIR+(nf_u32)id*EX_DIR_BYTES,ex_record,EX_DIR_BYTES))return nf_error;
    strcpy(ex_path,(char*)ex_record);cluster=rd16(ex_record+80);parent=rd16(ex_record+82);
    ex_first=cluster;ex_parent=id;ex_parent_first=0;
    if(id){if(read_at(EX_DIR+(nf_u32)parent*EX_DIR_BYTES+80,pair,2))return nf_error;ex_parent_first=rd16(pair);}
    count=0;end=0;
    do{
        if(count++>ex_clusters)return fail(NF_E_SOURCE);
        offset=id?ex_data+(nf_u32)(cluster-2U)*ex_spc*512UL:ex_root;
        slot=0;
        for(index=0;index<(id?(nf_u16)ex_spc*16U:ex_roots);index++,slot++){
            nf_debug_entry=index;
            if(ex_read(offset+(nf_u32)index*32UL,raw,32))return nf_error;
            memcpy(ex_raw,raw,32);
            if(id&&count==1&&index<2){
                memset(namebuf,' ',11);namebuf[0]='.';if(index)namebuf[1]='.';
                if(memcmp(ex_raw,namebuf,11)||ex_raw[11]!=0x10||rd32(ex_raw+28)||rd16(ex_raw+26)!=(index?ex_parent_first:ex_first))return fail(NF_E_SOURCE);
                continue;
            }
            if(!ex_raw[0]){end=1;break;}if(ex_raw[0]==0xe5)continue;
            if(ex_add(id))return nf_error;
        }
        if(!id||end)break;
        cluster=ex_fat(cluster);if(nf_error)return nf_error;
    }while(!ex_eoc(cluster));
    return 0;
}
nf_u8 nf_import_existing(nf_u32 bytes) {
    nf_u8 profile,i;nf_u16 c,value;nf_u32 n;
    nf_debug_stage=1;
    if(check())return nf_error;
    if(entries||ready||nf_pending||ex_valid)return fail(NF_E_STATE);
    if(bytes!=2097152UL&&bytes!=20971520UL)return fail(NF_E_SOURCE);
    profile=bytes==20971520UL;ex_bytes=bytes;ex_valid=0;
    ex_width=profile?16:12;ex_spc=profile?4:8;ex_spf=profile?40:2;ex_roots=512;
    ex_root=(16UL+1UL+2UL*ex_spf)*512UL;ex_data=ex_root+16384UL;
    ex_clusters=(nf_u16)((bytes-ex_data)/((nf_u32)ex_spc*512UL));
    if(ex_read(0,nf_sector,512))return nf_error;
    if(rd16(nf_sector+510)!=0xaa55||nf_sector[450]!=(profile?4:1)||rd32(nf_sector+454)!=16UL||rd32(nf_sector+458)!=(profile?40944UL:4080UL))return fail(NF_E_SOURCE);
    for(i=0;i<48;i++)if(nf_sector[462+i])return fail(NF_E_SOURCE);
    if(ex_read(8192UL,nf_sector,512))return nf_error;
    if(rd16(nf_sector+11)!=512||nf_sector[13]!=ex_spc||rd16(nf_sector+14)!=1||nf_sector[16]!=2||rd16(nf_sector+17)!=512||rd16(nf_sector+19)!=(profile?40944U:4080U)||nf_sector[21]!=0xf8||rd16(nf_sector+22)!=ex_spf||rd16(nf_sector+24)!=16||rd16(nf_sector+26)!=(profile?4:2)||rd32(nf_sector+28)!=16||rd16(nf_sector+510)!=0xaa55)return fail(NF_E_SOURCE);
    for(c=0;c<ex_spf;c++){
        n=8704UL+(nf_u32)c*512UL;
        if(ex_read(n,nf_sector,512)||ex_read(n+(nf_u32)ex_spf*512UL,compare,512))return nf_error;
        if(memcmp(nf_sector,compare,512))return fail(NF_E_SOURCE);
        if(write_at(EX_FAT+(nf_u32)c*512UL,nf_sector,512))return nf_error;
    }
    if(ex_fat(0)!=(ex_width==16?0xfff8U:0xff8U)||!ex_eoc(ex_fat(1)))return fail(NF_E_SOURCE);
    memset(nf_sector,0,512);for(c=0;c<3;c++)if(write_at(EX_OWN+(nf_u32)c*512UL,nf_sector,512))return nf_error;
    ex_dirs=1;ex_seen=0;ex_label=0;import_path[0]=0;if(ex_save_dir(0,0,0))return nf_error;
    nf_debug_stage=2;for(c=0;c<ex_dirs;c++){nf_debug_dir=c;if(ex_scan(c))return nf_error;}
    nf_debug_stage=3;for(c=2;c<=ex_clusters+1U;c++){nf_debug_cluster=c;
        value=ex_fat(c);if(nf_error)return nf_error;
        if(value&&value!=(ex_width==16?0xfff7U:0xff7U)){
            if(!ex_owned(c))return fail(NF_E_SOURCE);
        }
    }
    ex_valid=1;return 0;
}
static nf_u8 existing_payload(nf_u32 offset,nf_u16 n) {
    nf_u16 index;
    if(!ex_valid)return fail(NF_E_STATE);
    index=(nf_u16)(offset/((nf_u32)ex_spc*512UL));
    while(source_index<index){source_cluster=ex_fat(source_cluster);if(nf_error)return nf_error;source_index++;}
    return ex_read(ex_data+(nf_u32)(source_cluster-2U)*ex_spc*512UL+offset%((nf_u32)ex_spc*512UL),nf_sector,n);
}
