/* Guest probe for the GPU module: what pci.hidd, the display drivers and
 * the telemetry classes answer on this system, unprocessed. Read-only.
 *     gpuprobe
 * Prints to standard output. Compare with `fastfetch -s GPU --gpu-temp true
 * --format json`: every value fastfetch shows must be traceable here. */
#define __OOP_NOATTRBASES__
#define __OOP_NOMETHODBASES__

#include <exec/execbase.h>
#include <aros/asmcall.h>
#include <utility/hooks.h>
#include <utility/tagitem.h>
#include <oop/oop.h>
#include <hidd/hidd.h>
#include <hidd/pci.h>
#include <hidd/gfx.h>
#include <proto/exec.h>
#include <proto/oop.h>

#include <stdio.h>
#include <string.h>

/* Numbers of interfaces newer than some SDKs (see gpu_aros.c) */
#define REL_ANY 0u
#define HIDD_DEVICE_PATH 12u
#define HIDD_ENUM_RELATIONS 2u
#define TELEMETRY_ENTRY_COUNT 0u
#define TELEMETRY_GET_ENTRY_ATTRIBS 0u
#define TELEMETRY_TAG(n) (TAG_USER + 0x1000 + (n)) /* ID, Units, Min, Max, Value */
#define THERMAL_GET_TEMPERATURE 0u

struct Relation { ULONG type; OOP_Object *object; CONST_STRPTR path, label; };
struct pEnumRelations { OOP_MethodID mID; ULONG type; struct Hook *callback; APTR hookMsg; };
struct pGetEntryAttribs { OOP_MethodID mID; ULONG index; struct TagItem *tags; };
struct pGetTemperature { OOP_MethodID mID; ULONG point; LONG *temperature; };

#define MAXOBJ 32
struct Collect { ULONG count; OOP_Object *objects[MAXOBJ]; ULONG types[MAXOBJ]; char paths[MAXOBJ][48]; };

struct Library *OOPBase;
static OOP_AttrBase hiddAB, pciAB, gfxAB, telemetryAB;
static BOOL relations;

static void version(CONST_STRPTR name)
{
    struct Library *lib;
    Forbid();
    lib = (struct Library *)FindName(&SysBase->LibList, name);
    if (lib)
        printf("%s: %u.%u\n", (const char *)name, lib->lib_Version, lib->lib_Revision);
    else
        printf("%s: not in the library list\n", (const char *)name);
    Permit();
}

static BOOL isA(OOP_Object *o, const char *id)
{
    OOP_Class *cl;
    for (cl = OOP_OCLASS(o); cl; cl = cl->superclass)
        if (cl->ClassNode.ln_Name && !strcmp(cl->ClassNode.ln_Name, id))
            return TRUE;
    return FALSE;
}

static void classChain(const char *indent, OOP_Object *o)
{
    OOP_Class *cl;
    printf("%sclass:", indent);
    for (cl = OOP_OCLASS(o); cl; cl = cl->superclass)
        printf(" %s", cl->ClassNode.ln_Name ? cl->ClassNode.ln_Name : "?");
    printf("\n");
}

static void hiddNames(const char *indent, OOP_Object *o)
{
    IPTR name = 0, hw = 0, producer = 0;
    OOP_GetAttr(o, hiddAB + aoHidd_Name, &name);
    OOP_GetAttr(o, hiddAB + aoHidd_HardwareName, &hw);
    OOP_GetAttr(o, hiddAB + aoHidd_ProducerName, &producer);
    printf("%sname: %s; hardware: %s; producer: %s\n", indent, name ? (char *)name : "(none)",
           hw ? (char *)hw : "(none)", producer ? (char *)producer : "(none)");
}

static void memory(const char *indent, OOP_Object *gfx)
{
    struct TagItem tags[] = {
        { tHidd_Gfx_MemTotal, ~(IPTR)0 }, { tHidd_Gfx_MemFree, ~(IPTR)0 },
        { tHidd_Gfx_MemAddressableTotal, ~(IPTR)0 }, { tHidd_Gfx_MemAddressableFree, ~(IPTR)0 },
        { TAG_DONE, 0 } };
    int i;
    OOP_GetAttr(gfx, gfxAB + aoHidd_Gfx_MemoryAttribs, (IPTR *)tags);
    printf("%sMemoryAttribs (total, free, addressable total, addressable free):", indent);
    for (i = 0; i < 4; i++)
    {
        if (tags[i].ti_Data == ~(IPTR)0)
            printf(" unanswered");
        else
            printf(" %llu", (unsigned long long)tags[i].ti_Data);
    }
    printf("\n");
}

static void telemetry(const char *indent, OOP_Object *o)
{
    IPTR count = 0;
    ULONG i;
    OOP_MethodID get = OOP_GetMethodID((CONST_STRPTR)"hidd.telemetry", TELEMETRY_GET_ENTRY_ATTRIBS);

    OOP_GetAttr(o, telemetryAB + TELEMETRY_ENTRY_COUNT, &count);
    printf("%stelemetry entries: %lu\n", indent, (unsigned long)count);
    for (i = 0; i < count && i < 64; i++)
    {
        IPTR id = 0, units = 0, min = 0, max = 0, value = 0;
        struct TagItem tags[] = {
            { TELEMETRY_TAG(0), (IPTR)&id }, { TELEMETRY_TAG(1), (IPTR)&units },
            { TELEMETRY_TAG(2), (IPTR)&min }, { TELEMETRY_TAG(3), (IPTR)&max },
            { TELEMETRY_TAG(4), (IPTR)&value }, { TAG_DONE, 0 } };
        struct pGetEntryAttribs msg = { get, i, tags };
        if (!OOP_DoMethod(o, &msg.mID))
            printf("%s  %lu: not answered\n", indent, (unsigned long)i);
        else
            printf("%s  %lu: %s = %ld (units %lu, %ld..%ld)\n", indent, (unsigned long)i,
                   id ? (char *)id : "?", (long)(LONG)value, (unsigned long)(ULONG)units,
                   (long)(LONG)min, (long)(LONG)max);
    }
    if (isA(o, "hidd.telemetry.thermal"))
    {
        LONG t = 0;
        struct pGetTemperature msg = { OOP_GetMethodID((CONST_STRPTR)"hidd.telemetry.thermal", THERMAL_GET_TEMPERATURE), 0, &t };
        if (OOP_DoMethod(o, &msg.mID))
            printf("%sthermal current reading: %ld (thousandths of a degree Celsius)\n", indent, (long)t);
        else
            printf("%sthermal current reading: not answered\n", indent);
    }
}

AROS_UFH3(BOOL, collectHook, AROS_UFHA(struct Hook *, hook, A0), AROS_UFHA(APTR, object, A2), AROS_UFHA(APTR, message, A1))
{
    AROS_USERFUNC_INIT
    struct Collect *c = hook->h_Data;
    (void)message;
    if (c->count < MAXOBJ)
        c->objects[c->count++] = object;
    return FALSE;
    AROS_USERFUNC_EXIT
}

AROS_UFH3(BOOL, relationHook, AROS_UFHA(struct Hook *, hook, A0), AROS_UFHA(struct Relation *, rel, A2), AROS_UFHA(APTR, message, A1))
{
    AROS_USERFUNC_INIT
    struct Collect *c = hook->h_Data;
    (void)message;
    if (c->count < MAXOBJ)
    {
        c->objects[c->count] = rel->object;
        c->types[c->count] = rel->type;
        snprintf(c->paths[c->count], sizeof(c->paths[0]), "%s", rel->path ? (const char *)rel->path : "");
        c->count++;
    }
    return FALSE;
    AROS_USERFUNC_EXIT
}

static void relationsOf(const char *indent, OOP_Object *o)
{
    struct Collect c = { 0 };
    struct Hook hook = { .h_Entry = (HOOKFUNC)(APTR)AROS_ASMSYMNAME(relationHook), .h_Data = &c };
    struct pEnumRelations msg = { OOP_GetMethodID((CONST_STRPTR)IID_Hidd, HIDD_ENUM_RELATIONS), REL_ANY, &hook, NULL };
    ULONG i;

    OOP_DoMethod(o, &msg.mID);
    printf("%srelations: %lu\n", indent, (unsigned long)c.count);
    /* queried after the enumeration, outside the relation lock */
    for (i = 0; i < c.count; i++)
    {
        OOP_Object *r = c.objects[i];
        printf("%s  type 0x%08lx, path %s\n", indent, (unsigned long)c.types[i], c.paths[i][0] ? c.paths[i] : "(none)");
        if (!r)
            continue;
        classChain("      ", r);
        hiddNames("      ", r);
        if (isA(r, "hidd.gfx"))
            memory("      ", r);
        if (isA(r, "hidd.telemetry"))
            telemetry("      ", r);
    }
}

int main(void)
{
    struct Collect pcis = { 0 }, drivers = { 0 };
    OOP_Object *pci, *gfxhw;
    ULONG i;

    if (!(OOPBase = OpenLibrary((CONST_STRPTR)"oop.library", 0)))
    {
        printf("oop.library: not available\n");
        return 20;
    }
    version((CONST_STRPTR)"hiddclass.hidd");
    version((CONST_STRPTR)"telemetry.hidd");
    version((CONST_STRPTR)"pci.hidd");
    version((CONST_STRPTR)"gfx.hidd");
    Forbid();
    {
        struct Library *lib = (struct Library *)FindName(&SysBase->LibList, (CONST_STRPTR)"hiddclass.hidd");
        relations = lib && (lib->lib_Version > 1 || (lib->lib_Version == 1 && lib->lib_Revision >= 3));
    }
    Permit();
    printf("relations: %s\n", relations ? "available (hiddclass 1.3 or later)" : "not available");

    hiddAB = OOP_ObtainAttrBase((CONST_STRPTR)IID_Hidd);
    pciAB = OOP_ObtainAttrBase((CONST_STRPTR)IID_Hidd_PCIDevice);
    gfxAB = OOP_ObtainAttrBase((CONST_STRPTR)IID_Hidd_Gfx);
    telemetryAB = relations ? OOP_ObtainAttrBase((CONST_STRPTR)"hidd.telemetry") : 0;
    printf("attribute bases: hidd %s, pci device %s, gfx %s, telemetry %s\n", hiddAB ? "yes" : "no",
           pciAB ? "yes" : "no", gfxAB ? "yes" : "no", telemetryAB ? "yes" : "no");

    pci = (hiddAB && pciAB) ? OOP_NewObject(NULL, (CONST_STRPTR)CLID_Hidd_PCI, NULL) : NULL;
    if (!pci)
        printf("pci.hidd: no PCI subsystem object\n");
    else
    {
        struct Hook hook = { .h_Entry = (HOOKFUNC)(APTR)AROS_ASMSYMNAME(collectHook), .h_Data = &pcis };
        struct TagItem req[] = { { tHidd_PCI_Class, 0x03 }, { TAG_DONE, 0 } };
        struct pHidd_PCI_EnumDevices msg = { OOP_GetMethodID((CONST_STRPTR)IID_Hidd_PCI, moHidd_PCI_EnumDevices), &hook, req };
        OOP_DoMethod(pci, &msg.mID);
        printf("PCI display functions (class 0x03): %lu\n", (unsigned long)pcis.count);
    }
    for (i = 0; i < pcis.count; i++)
    {
        OOP_Object *d = pcis.objects[i];
        IPTR bus = 0, dev = 0, sub = 0, ven = 0, prod = 0, scl = 0, rev = 0, path = 0;
        OOP_GetAttr(d, pciAB + aoHidd_PCIDevice_Bus, &bus);
        OOP_GetAttr(d, pciAB + aoHidd_PCIDevice_Dev, &dev);
        OOP_GetAttr(d, pciAB + aoHidd_PCIDevice_Sub, &sub);
        OOP_GetAttr(d, pciAB + aoHidd_PCIDevice_VendorID, &ven);
        OOP_GetAttr(d, pciAB + aoHidd_PCIDevice_ProductID, &prod);
        OOP_GetAttr(d, pciAB + aoHidd_PCIDevice_SubClass, &scl);
        OOP_GetAttr(d, pciAB + aoHidd_PCIDevice_RevisionID, &rev);
        if (relations)
            OOP_GetAttr(d, hiddAB + HIDD_DEVICE_PATH, &path);
        printf("PCI %02lx:%02lx.%lx %04lx:%04lx subclass 0x%02lx revision 0x%02lx path %s\n",
               (unsigned long)bus, (unsigned long)dev, (unsigned long)sub, (unsigned long)ven,
               (unsigned long)prod, (unsigned long)scl, (unsigned long)rev,
               path ? (char *)path : "(none)");
        if (relations)
            relationsOf("  ", d);
    }

    gfxhw = OOP_NewObject(NULL, (CONST_STRPTR)CLID_HW_Gfx, NULL);
    if (gfxhw)
    {
        struct Hook hook = { .h_Entry = (HOOKFUNC)(APTR)AROS_ASMSYMNAME(collectHook), .h_Data = &drivers };
        struct pHW_EnumDrivers msg = { OOP_GetMethodID((CONST_STRPTR)IID_HW, moHW_EnumDrivers), &hook, NULL };
        OOP_DoMethod(gfxhw, &msg.mID);
    }
    printf("graphics drivers: %lu\n", (unsigned long)drivers.count);
    for (i = 0; i < drivers.count; i++)
    {
        printf("driver %lu\n", (unsigned long)i);
        classChain("  ", drivers.objects[i]);
        hiddNames("  ", drivers.objects[i]);
        memory("  ", drivers.objects[i]);
        if (relations)
            relationsOf("  ", drivers.objects[i]);
    }

    if (telemetryAB)
        OOP_ReleaseAttrBase((CONST_STRPTR)"hidd.telemetry");
    if (gfxAB)
        OOP_ReleaseAttrBase((CONST_STRPTR)IID_Hidd_Gfx);
    if (pciAB)
        OOP_ReleaseAttrBase((CONST_STRPTR)IID_Hidd_PCIDevice);
    if (hiddAB)
        OOP_ReleaseAttrBase((CONST_STRPTR)IID_Hidd);
    CloseLibrary(OOPBase);
    return 0;
}
