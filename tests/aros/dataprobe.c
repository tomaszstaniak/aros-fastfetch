/* Guest probe: what the AROS interfaces a fastfetch backend would read
 * actually return on this system. Read-only; opens no requesters.
 *     dataprobe LOGFILE
 * One "key: value" line per fact; a failed source says so instead of 0. */
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/intuition.h>
#include <proto/graphics.h>
#include <proto/locale.h>
#include <proto/aros.h>
#include <proto/processor.h>
#include <proto/timer.h>
#include <aros/inquire.h>
#include <resources/processor.h>
#include <devices/timer.h>
#include <dos/dosextens.h>
#include <exec/execbase.h>
#include <exec/resident.h>
#include <graphics/gfxbase.h>
#include <graphics/displayinfo.h>
#include <intuition/screens.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/utsname.h>

static FILE *out;
#define P(...) fprintf(out, __VA_ARGS__)

static void inquire(void)
{
    struct Library *ArosBase = OpenLibrary((CONST_STRPTR)"aros.library", 0);
    IPTR version = 0, major = 0, minor = 0, rdate = 0, bdate = 0, abi = 0;
    STRPTR variant = NULL, arch = NULL;
    if (!ArosBase) { P("aros.library: unavailable\n"); return; }
    ArosInquire(AI_ArosVersion, (IPTR)&version, AI_ArosReleaseMajor, (IPTR)&major,
                AI_ArosReleaseMinor, (IPTR)&minor, AI_ArosReleaseDate, (IPTR)&rdate,
                AI_ArosBuildDate, (IPTR)&bdate, AI_ArosVariant, (IPTR)&variant,
                AI_ArosArchitecture, (IPTR)&arch, AI_ArosABIMajor, (IPTR)&abi, TAG_DONE);
    P("aros.library: %u.%u\n", ArosBase->lib_Version, ArosBase->lib_Revision);
    P("inquire.version: %lu\ninquire.release: %lu.%lu\n", (unsigned long)version,
      (unsigned long)major, (unsigned long)minor);
    P("inquire.release_date: %lu\ninquire.build_date: %lu\n", (unsigned long)rdate, (unsigned long)bdate);
    P("inquire.variant: %s\ninquire.architecture: %s\ninquire.abi_major: %lu\n",
      variant ? (char *)variant : "(null)", arch ? (char *)arch : "(null)", (unsigned long)abi);
    CloseLibrary(ArosBase);
}

static void processor(void)
{
    APTR ProcessorBase = OpenResource((CONST_STRPTR)PROCESSORNAME);
    ULONG count = 0, i;
    if (!ProcessorBase) { P("processor.resource: unavailable\n"); return; }
    GetCPUInfoTags(GCIT_NumberOfProcessors, (IPTR)&count, TAG_DONE);
    P("cpu.count: %lu\n", (unsigned long)count);
    for (i = 0; i < count && i < 4; i++) {
        CONST_STRPTR model = NULL;
        UQUAD speed = 0, fsb = 0;
        ULONG family = 0, archv = 0, vendor = 0;
        GetCPUInfoTags(GCIT_SelectedProcessor, i, GCIT_ModelString, (IPTR)&model,
                       GCIT_ProcessorSpeed, (IPTR)&speed, GCIT_FrontsideSpeed, (IPTR)&fsb,
                       GCIT_Family, (IPTR)&family, GCIT_Architecture, (IPTR)&archv,
                       GCIT_Vendor, (IPTR)&vendor, TAG_DONE);
        P("cpu%lu.model: %s\ncpu%lu.speed_hz: %llu\ncpu%lu.fsb_hz: %llu\n", (unsigned long)i,
          model ? (const char *)model : "(null)", (unsigned long)i, (unsigned long long)speed,
          (unsigned long)i, (unsigned long long)fsb);
        P("cpu%lu.family: %lu\ncpu%lu.arch: %lu\ncpu%lu.vendor: %lu\n", (unsigned long)i,
          (unsigned long)family, (unsigned long)i, (unsigned long)archv, (unsigned long)i, (unsigned long)vendor);
    }
}

static void uptime(void)
{
    struct MsgPort *port = CreateMsgPort();
    struct timerequest *tr = port ? (struct timerequest *)CreateIORequest(port, sizeof *tr) : NULL;
    if (tr && !OpenDevice((CONST_STRPTR)TIMERNAME, UNIT_MICROHZ, (struct IORequest *)tr, 0)) {
        struct Device *TimerBase = tr->tr_node.io_Device;
        struct timeval tv = { 0 };
        GetUpTime(&tv);
        P("timer.version: %u.%u\nuptime.seconds: %lu\n", TimerBase->dd_Library.lib_Version,
          TimerBase->dd_Library.lib_Revision, (unsigned long)tv.tv_secs);
        CloseDevice((struct IORequest *)tr);
    } else P("timer.device: unavailable\n");
    if (tr) DeleteIORequest((struct IORequest *)tr);
    if (port) DeleteMsgPort(port);
}

static void display(void)
{
    struct Screen *s = LockPubScreen(NULL);
    struct NameInfo name;
    ULONG mode;
    if (!s) { P("screen: none\n"); return; }
    mode = GetVPModeID(&s->ViewPort);
    P("screen.title: %s\nscreen.size: %dx%d\nscreen.depth: %lu\nscreen.mode_id: 0x%08lx\n",
      s->Title ? (char *)s->Title : "(null)", s->Width, s->Height,
      (unsigned long)GetBitMapAttr(s->RastPort.BitMap, BMA_DEPTH), (unsigned long)mode);
    if (mode != INVALID_ID && GetDisplayInfoData(NULL, (UBYTE *)&name, sizeof name, DTAG_NAME, mode))
        P("screen.mode_name: %s\n", (char *)name.Name);
    else P("screen.mode_name: unavailable\n");
    if (s->Font) P("screen.font: %s %u\n", (char *)s->Font->ta_Name, s->Font->ta_YSize);
    UnlockPubScreen(NULL, s);
    if (GfxBase->DefaultFont)
        P("gfx.default_font: %s %u\n", (char *)GfxBase->DefaultFont->tf_Message.mn_Node.ln_Name,
          GfxBase->DefaultFont->tf_YSize);
    P("graphics.version: %u.%u\nintuition.version: %u.%u\n", GfxBase->LibNode.lib_Version,
      GfxBase->LibNode.lib_Revision, IntuitionBase->LibNode.lib_Version, IntuitionBase->LibNode.lib_Revision);
}

static void locale(void)
{
    struct Locale *l = OpenLocale(NULL);
    if (!l) { P("locale: unavailable\n"); return; }
    P("locale.name: %s\nlocale.language: %s\nlocale.country_code: 0x%08lx\nlocale.gmt_offset_min: %ld\n",
      l->loc_LocaleName ? (char *)l->loc_LocaleName : "(null)",
      l->loc_LanguageName ? (char *)l->loc_LanguageName : "(null)",
      (unsigned long)l->loc_CountryCode, (long)l->loc_GMTOffset);
    CloseLocale(l);
}

static void volumes(void)
{
    struct DosList *dl;
    char names[16][64];
    int n = 0, i;
    struct Process *me = (struct Process *)FindTask(NULL);
    APTR win = me->pr_WindowPtr;
    me->pr_WindowPtr = (APTR)-1;
    dl = LockDosList(LDF_VOLUMES | LDF_READ);
    while (n < 16 && (dl = NextDosEntry(dl, LDF_VOLUMES))) {
        const char *b = (const char *)AROS_BSTR_ADDR(dl->dol_Name);
        int len = (int)AROS_BSTR_strlen(dl->dol_Name);
        if (len > 60) len = 60;
        memcpy(names[n], b, (size_t)len); names[n][len] = ':'; names[n][len + 1] = 0; n++;
    }
    UnLockDosList(LDF_VOLUMES | LDF_READ);
    for (i = 0; i < n; i++) {
        BPTR lock = Lock((CONST_STRPTR)names[i], ACCESS_READ);
        struct InfoData id;
        if (lock && Info(lock, &id))
            P("volume: %s blocks=%ld used=%ld bpb=%ld type=0x%08lx state=%ld\n", names[i],
              (long)id.id_NumBlocks, (long)id.id_NumBlocksUsed, (long)id.id_BytesPerBlock,
              (unsigned long)id.id_DiskType, (long)id.id_DiskState);
        else P("volume: %s info-failed ioerr=%ld\n", names[i], (long)IoErr());
        if (lock) UnLock(lock);
    }
    me->pr_WindowPtr = win;
}

static void tasks(void)
{
    struct Library *wb;
    struct Resident *r;
    struct CommandLineInterface *cli = Cli();
    BPTR out_fh = Output();
    Forbid();
    P("task.Wanderer: %s\n", FindTask((CONST_STRPTR)"Wanderer") ? "yes" : "no");
    P("task.Workbench: %s\n", FindTask((CONST_STRPTR)"Workbench") ? "yes" : "no");
    Permit();
    wb = OpenLibrary((CONST_STRPTR)"workbench.library", 0);
    if (wb) { P("workbench.version: %u.%u\n", wb->lib_Version, wb->lib_Revision); CloseLibrary(wb); }
    P("dos.version: %u.%u\nexec.version: %u.%u\n", DOSBase->dl_lib.lib_Version, DOSBase->dl_lib.lib_Revision,
      SysBase->LibNode.lib_Version, SysBase->LibNode.lib_Revision);
    r = FindResident((CONST_STRPTR)"shell");
    P("resident.shell: %s\n", r && r->rt_IdString ? (char *)r->rt_IdString : "(none)");
    r = FindResident((CONST_STRPTR)"Shell");
    P("resident.Shell: %s\n", r && r->rt_IdString ? (char *)r->rt_IdString : "(none)");
    if (cli && cli->cli_CommandName)
        P("cli.command_name: %.*s\n", (int)AROS_BSTR_strlen(cli->cli_CommandName),
          (const char *)AROS_BSTR_ADDR(cli->cli_CommandName));
    if (out_fh) {
        struct FileHandle *fh = BADDR(out_fh);
        struct MsgPort *port = fh->fh_Type;
        P("output.interactive: %ld\n", (long)IsInteractive(out_fh));
        if (port && port->mp_SigTask)
            P("output.handler_task: %s\n", ((struct Task *)port->mp_SigTask)->tc_Node.ln_Name);
    }
    Forbid();
    P("library.bsdsocket_resident: %s\n", FindName(&SysBase->LibList, (CONST_STRPTR)"bsdsocket.library") ? "yes" : "no");
    Permit();
}

static void posix(void)
{
    struct utsname u;
    const char *e;
    if (uname(&u) == 0)
        P("uname: sysname=%s nodename=%s release=%s version=%s machine=%s\n", u.sysname, u.nodename,
          u.release, u.version, u.machine);
    else P("uname: failed\n");
    e = getenv("USER"); P("env.USER: %s\n", e ? e : "(unset)");
    e = getenv("HOSTNAME"); P("env.HOSTNAME: %s\n", e ? e : "(unset)");
    e = getenv("HOME"); P("env.HOME: %s\n", e ? e : "(unset)");
    e = getenv("COLORTERM"); P("env.COLORTERM: %s\n", e ? e : "(unset)");
    e = getenv("TERM"); P("env.TERM: %s\n", e ? e : "(unset)");
    e = getenv("LANG"); P("env.LANG: %s\n", e ? e : "(unset)");
    e = getenv("CHARSET"); P("env.CHARSET: %s\n", e ? e : "(unset)");
}

int main(int argc, char **argv)
{
    if (argc != 2) return 20;
    out = fopen(argv[1], "w");
    if (!out) return 20;
    P("exec.memory.total_any: %lu\nexec.memory.free_any: %lu\nexec.memory.largest: %lu\n",
      (unsigned long)AvailMem(MEMF_TOTAL | MEMF_ANY), (unsigned long)AvailMem(MEMF_ANY),
      (unsigned long)AvailMem(MEMF_ANY | MEMF_LARGEST));
    P("exec.memory.total_chip: %lu\nexec.memory.total_fast: %lu\n",
      (unsigned long)AvailMem(MEMF_TOTAL | MEMF_CHIP), (unsigned long)AvailMem(MEMF_TOTAL | MEMF_FAST));
    inquire(); processor(); uptime(); display(); locale(); volumes(); tasks(); posix();
    P("done\n");
    fclose(out);
    return 0;
}
