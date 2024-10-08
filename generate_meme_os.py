#!/usr/bin/python3
# RISC-VGA example: by Brent Hartshorn
# install: sudo apt-get install gcc-riscv64-unknown-elf qemu-system-riscv64
import os, sys, subprocess
from random import choice

def image2c( path, name=None, colors=16, debug=False ):
	from PIL import Image
	if name is None:
		p,name = os.path.split(path)
		name = name.replace(' ', '_').replace('.', '_').replace('-','_')

	img = Image.open(path).convert('RGB')
	img = img.resize( (320, 200) )
	pimg = Image.new('P', (320,200) )
	pimg.putpalette(vga_pal)
	img = img.quantize(palette=pimg)
	img = img.convert('P', colors=colors)
	if debug:
		img.save('/tmp/%s.gif' % name)

	pix = [str(v) for v in img.getdata()]
	c = [
		'for (int i=0; i<sizeof(%s); i++){' % name,
		'	((volatile u8*)0x50000000)[i] = %s[i];' % name,
		'}',
	]
	o = {
		'data'  : 'const unsigned char %s[%s] = {%s};'  % (name, len(pix), ','.join(pix)),
		'name'  : name,
		'redraw': '\n'.join(c),
		'len'   : len(pix)
	}
	return o


def gen_proc_header(images):
	out = [
		PROC_H,
		'i32 active_pid;',
		'struct proc proc_list[PROC_NAME_MAXLEN] = {};',
	]
	for o in images:
		out.append(o['data'])
	return out

def gen_procs(images, strings, stack_mb=1):
	assert images
	out = []
	for p, o in enumerate(images):
		out += [
			'u8 __proc_%s_stack[%s];' % (p, int(1024*1024*stack_mb) ),
			'void *__proc_%s_stack_top = &__proc_%s_stack[sizeof(__proc_%s_stack) - 1];' % (p,p,p),
			'void __proc_entry_%s(){' % p,
			'	uart_print("[PID = %s] proc entry!\\n");' % p,
			'	while (true){',
			'		uart_print("%s");' % strings[p],
			o['redraw'],
			'	}',
			'	uart_print("[PID = %s] Hello, Process Shceduler!\\n");' % p,
			'}',
		]
	return out

PROC_H = '''
#define PROC_NAME_MAXLEN 64
#define PROC_TOTAL_COUNT 16

enum proc_state {
  PROC_STATE_NONE = 0,
  PROC_STATE_READY,
  PROC_STATE_RUNNING,
};

struct proc {
  enum proc_state state;
  u32 pid;
  u8 name[PROC_NAME_MAXLEN];
  struct cpu cpu;
  u64 hartid;
};
'''

VGA_S = r'''
	# PCI is at 0x30000000
	# VGA is at 00:01.0, using extended control regs (4096 bytes)
	# TODO: Scan for Vendor ID / Product ID
	la t0, 0x30000000|(1<<15)|(0<<12)
	# Set up frame buffer
	la t1, 0x50000008
	sw t1, 0x10(t0)
	# Set up I/O
	la t2, 0x40000000
	sw t2, 0x18(t0)
	# Enable memory accesses for this device
	lw a0, 0x04(t0)
	ori a0, a0, 0x02
	sw a0, 0x04(t0)
	lw a0, 0x04(t0)
	# Set up video mode somehow
	li t3, 0x60 # Enable LFB, enable 8-bit DAC
	sh t3, 0x508(t2)
	# Set Mode 13h by hand
	la a0, mode_13h_regs
	addi a1, t2, 0x400-0xC0
	la t3, 0xC0
	1:
		# Grab address
		lbu a3, 0(a0)
		beq a3, zero, 2f
		add a2, a1, a3
		# Grab index and data
		lb a4, 1(a0)
		lbu a5, 2(a0)
		# Advance a0
		addi a0, a0, 3
		# If this is for the attribute controller, treat it specially.
		blt a3, t3, 3f
		# If this is an external register, also treat it specially.
		blt a4, zero, 4f
			# Normal case
			sb a4, 0(a2)
			sb a5, 1(a2)
			j 1b
		3:
			# The attribute controller is a special case
			lb zero, 0xDA(a1)
			sb a4, 0(a2)
			sb a5, 0(a2)
			j 1b
		4:
			# External registers are also special but not as special as the attribute controller
			sb a5, 0(a2)
			j 1b
	2:
	# Set up a palette
	li t3, 0
	sb t3, 0x408(t2)
	li t3, 0
	li t4, 256*3
	la a0, initial_palette
	1:
		lb t5, 0(a0)
		sb t5, 0x409(t2)
		addi a0, a0, 1
		addi t3, t3, 1
		bltu t3, t4, 1b

'''

START_VGA_S = f'''
.text
.global _start
_start:
  bne a0, x0, _start # loop if hartid is not 0
  li sp, 0x80200000 # setup stack pointer
  {VGA_S}
  j firmware_main # jump to c entry
'''

def gen_trap_s():
	s = ['''
.equ REGSZ, 8
.global trap_entry
trap_entry:
	# swap x5/mscratch
	csrrw x5, mscratch, x5
	# use x5 as cpu state base address register
	la x5, trap_cpu
	# save general purpose registers, x0 ~ x4
	sd x0, (0 * REGSZ)(x5)
	sd x1, (1 * REGSZ)(x5)
	sd x2, (2 * REGSZ)(x5)
	sd x3, (3 * REGSZ)(x5)
	sd x4, (4 * REGSZ)(x5)
	# save origin x5 by x1, which has been saved
	csrr x1, mscratch
	sd x1, (5 * REGSZ)(x5)
	''',
	'\n'.join(['sd x%s, (%s*REGSZ)(x5)' %(i,i) for i in range(6,32)]),
	'''
	# save privilege registers
	# save mepc by x1, which has been saved
	csrr x1, mepc
	sd x1, (32 * REGSZ)(x5)
	# call trap_handler, Need set stack pointer?
	la t0, trap_stack_top
	ld sp, 0(t0)
	call trap_handler
	# use x5 as cpu state base address register
	la x5, trap_cpu
	# restore privilege registers
	# restore mepc by x1, which will be restored later
	ld x1, (32 * REGSZ)(x5)
	csrw mepc, x1
	# restore general purpose registers, x0 ~ x4
	ld x0, (0 * REGSZ)(x5)
	ld x1, (1 * REGSZ)(x5)
	ld x2, (2 * REGSZ)(x5)
	ld x3, (3 * REGSZ)(x5)
	ld x4, (4 * REGSZ)(x5)
	# postpone the restoration of x5 because it is being used as the base address register
	''',
	'\n'.join(['ld x%s, (%s*REGSZ)(x5)' %(i,i) for i in range(6,32)]),
	'ld x5, (6 * REGSZ)(x5)',
	'mret'
	]
	return '\n'.join(s)

TRAP_C = r'''
struct cpu trap_cpu;
u8 trap_stack[1 << 20];
void *trap_stack_top = &trap_stack[sizeof(trap_stack) - 1];

void trap_handler() {
  u64 mcause = csrr_mcause();
  switch (mcause){
	  case MCAUSE_INTR_M_TIMER: {
	    if (proc_list[0].state != PROC_STATE_NONE){ // there exists runnable processes
	      // assume proc-0 is the active process if there is no active process
	      if (active_pid < 0){
	        active_pid = 0;
	        trap_cpu = proc_list[0].cpu;
	        uart_print("[Trap - M-mode Timer] Scheduler Init.\n");
	      }
	      
	      proc_list[active_pid].cpu = trap_cpu; // save cpu state for the active process
	      proc_list[active_pid].state = PROC_STATE_READY; // suspend the active process

	      // iterate the processes from the next process, ending with the active process
	      for (int ring_index = 1; ring_index <= PROC_TOTAL_COUNT; ring_index++){
	        int real_index = (active_pid + ring_index) % PROC_TOTAL_COUNT;
	        struct proc *proc = &proc_list[real_index];
	        if (proc->state == PROC_STATE_READY){
	          trap_cpu = proc->cpu;
	          active_pid = proc->pid;
	          break;
	        }
	      }
	    }
	    set_timeout(10000000);
	    break;
	  }

	  case MCAUSE_INTR_M_EXTER: {
	    uart_print("[Trap - M-mode Exter]\n");
	    break;
	  }

	  case MCAUSE_INNER_M_ILLEAGEL_INSTRUCTION: {
	    uart_print("[Trap - M-mode Illeagel Instruction]\n");
	    break;
	  }

	  default: {
	    uart_print("[Trap - Default]\n");
	    break;
	  }
  }
}
'''

ARCH = '''
#define MACHINE_BITS 64
#define BITS_PER_LONG MACHINE_BITS
#define bool _Bool
#define true 1
#define false 0
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;
typedef signed char i8;
typedef signed short i16;
typedef signed int i32;
typedef signed long i64;
typedef u64 size_t;
'''

CPU = 'struct cpu {%s} __attribute__((packed));' % '\n'.join(['u64 x%s;' % i for i in range(32)]+['u64 pc;'])

TIMER = '''
#define MTIME 0x200bff8
#define MTIMECMP_0 0x2004000
static inline u64 mtime() { return readu64(MTIME); }
static inline u64 mtimecmp_0() { return readu64(MTIMECMP_0); }
static inline u64 set_timeout(u64 timeout) { writeu64(MTIMECMP_0, mtime() + timeout); }
'''

ARCH_ASM = '''
#define readu8(addr) (*(const u8 *)(addr))
#define readu16(addr) (*(const u16 *)(addr))
#define readu32(addr) (*(const u32 *)(addr))
#define readu64(addr) (*(const u64 *)(addr))
#define writeu8(addr, val) (*(u8 *)(addr) = (val))
#define writeu16(addr, val) (*(u16 *)(addr) = (val))
#define writeu32(addr, val) (*(u32 *)(addr) = (val))
#define writeu64(addr, val) (*(u64 *)(addr) = (val))

static inline void csrw_mtvec(const volatile u64 val) { asm volatile("csrw mtvec, %0" :: "r"(val)); }
static inline void csrw_mie(const volatile u64 val) { asm volatile("csrw mie, %0" :: "r"(val)); }
static inline void csrs_mstatus(const volatile u64 val) { asm volatile("csrs mstatus, %0" :: "r"(val)); }
static inline u64 csrr_mcause(){
  volatile u64 val;
  asm volatile("csrr %0, mcause" : "=r"(val) :);
  return val;
}
'''

INTERRUPTS = '''
#define MSTAUTS_MIE (0x1L << 3)
#define MIE_MTIE (0x1L << 7)
#define MIE_MEIE (0x1L << 11)
#define MCAUSE_INTR_M_TIMER ((0x1L << (MACHINE_BITS - 1)) | 7)
#define MCAUSE_INTR_M_EXTER ((0x1L << (MACHINE_BITS - 1)) | 11)
#define MCAUSE_INNER_M_ILLEAGEL_INSTRUCTION (0x2L)
'''

UART = '''
#define UART_BASE 0x10000000
#define UART_RBR_OFFSET 0  /* In:  Recieve Buffer Register */
#define UART_THR_OFFSET 0  /* Out: Transmitter Holding Register */
#define UART_DLL_OFFSET 0  /* Out: Divisor Latch Low */
#define UART_IER_OFFSET 1  /* I/O: Interrupt Enable Register */
#define UART_DLM_OFFSET 1  /* Out: Divisor Latch High */
#define UART_FCR_OFFSET 2  /* Out: FIFO Control Register */
#define UART_IIR_OFFSET 2  /* I/O: Interrupt Identification Register */
#define UART_LCR_OFFSET 3  /* Out: Line Control Register */
#define UART_MCR_OFFSET 4  /* Out: Modem Control Register */
#define UART_LSR_OFFSET 5  /* In:  Line Status Register */
#define UART_MSR_OFFSET 6  /* In:  Modem Status Register */
#define UART_SCR_OFFSET 7  /* I/O: Scratch Register */
#define UART_MDR1_OFFSET 8 /* I/O:  Mode Register */
#define PLATFORM_UART_INPUT_FREQ 10000000
#define PLATFORM_UART_BAUDRATE 115200
static u8 *uart_base_addr = (u8 *)UART_BASE;
static void set_reg(u32 offset, u32 val){ writeu8(uart_base_addr + offset, val);}
static u32 get_reg(u32 offset){ return readu8(uart_base_addr + offset);}
static void uart_putc(u8 ch){ set_reg(UART_THR_OFFSET, ch);}
static void uart_print(char *str){ while (*str) uart_putc(*str++);}

static inline void uart_init(){
  u16 bdiv = (PLATFORM_UART_INPUT_FREQ + 8 * PLATFORM_UART_BAUDRATE) / (16 * PLATFORM_UART_BAUDRATE);
  set_reg(UART_IER_OFFSET, 0x00); /* Disable all interrupts */
  set_reg(UART_LCR_OFFSET, 0x80); /* Enable DLAB */
  if (bdiv) {
    set_reg(UART_DLL_OFFSET, bdiv & 0xff); /* Set divisor low byte */
    set_reg(UART_DLM_OFFSET, (bdiv >> 8) & 0xff); /* Set divisor high byte */
  }
  set_reg(UART_LCR_OFFSET, 0x03); /* 8 bits, no parity, one stop bit */
  set_reg(UART_FCR_OFFSET, 0x01); /* Enable FIFO */
  set_reg(UART_MCR_OFFSET, 0x00); /* No modem control DTR RTS */
  get_reg(UART_LSR_OFFSET); /* Clear line status */
  get_reg(UART_RBR_OFFSET); /* Read receive buffer */  
  set_reg(UART_SCR_OFFSET, 0x00); /* Set scratchpad */
}
'''

LIBC = r'''
void *memset(void *s, int c, size_t n){
  unsigned char *p = s;
  while (n--) *p++ = (unsigned char)c;
  return s;
}
void *memcpy(void *dest, const void *src, size_t n){
  unsigned char *d = dest;
  const unsigned char *s = src;
  while (n--) *d++ = *s++;
  return dest;
}
#define VRAM ((volatile u8 *)0x50000000)
void putpixel(int x, int y, char c){
	VRAM[y*320 + x] = c;
}
'''

LINKER_SCRIPT = '''
ENTRY(_start)
MEMORY {} /* default */
. = 0x80000000;
SECTIONS {}
'''

MODE_13H = '''
mode_13h_regs:
	# Miscellaneous Output Register:
	# Just a single port. But bit 0 determines whether we use 3Dx or 3Bx.
	# So we need to set this early.
	.byte 0xC2, 0xFF, 0x63

	# Sequencer:
	# Disable reset here.
	.byte 0xC4, 0x00, 0x00

	# Attributes:
	# - Read 3DA to reset flip-flop
	# - Write 3C0 for address
	# - Write 3C0 for data
	.byte 0xC0, 0x00, 0x00
	.byte 0xC0, 0x01, 0x02
	.byte 0xC0, 0x02, 0x08
	.byte 0xC0, 0x03, 0x0A
	.byte 0xC0, 0x04, 0x20
	.byte 0xC0, 0x05, 0x22
	.byte 0xC0, 0x06, 0x28
	.byte 0xC0, 0x07, 0x2A
	.byte 0xC0, 0x08, 0x15
	.byte 0xC0, 0x09, 0x17
	.byte 0xC0, 0x0A, 0x1D
	.byte 0xC0, 0x0B, 0x1F
	.byte 0xC0, 0x0C, 0x35
	.byte 0xC0, 0x0D, 0x37
	.byte 0xC0, 0x0E, 0x3D
	.byte 0xC0, 0x0F, 0x3F

	.byte 0xC0, 0x30, 0x41
	.byte 0xC0, 0x31, 0x00
	.byte 0xC0, 0x32, 0x0F
	.byte 0xC0, 0x33, 0x00
	.byte 0xC0, 0x34, 0x00

	# Graphics Mode
	.byte 0xCE, 0x00, 0x00
	.byte 0xCE, 0x01, 0x00
	.byte 0xCE, 0x02, 0x00
	.byte 0xCE, 0x03, 0x00
	.byte 0xCE, 0x04, 0x00
	.byte 0xCE, 0x05, 0x40
	.byte 0xCE, 0x06, 0x05
	.byte 0xCE, 0x07, 0x00
	.byte 0xCE, 0x08, 0xFF

	# CRTC
	.byte 0xD4, 0x11, 0x0E # Do this to unprotect the registers

	.byte 0xD4, 0x00, 0x5F
	.byte 0xD4, 0x01, 0x4F
	.byte 0xD4, 0x02, 0x50
	.byte 0xD4, 0x03, 0x82
	.byte 0xD4, 0x04, 0x54
	.byte 0xD4, 0x05, 0x80
	.byte 0xD4, 0x06, 0xBF
	.byte 0xD4, 0x07, 0x1F
	.byte 0xD4, 0x08, 0x00
	.byte 0xD4, 0x09, 0x41
	.byte 0xD4, 0x0A, 0x20
	.byte 0xD4, 0x0B, 0x1F
	.byte 0xD4, 0x0C, 0x00
	.byte 0xD4, 0x0D, 0x00
	.byte 0xD4, 0x0E, 0xFF
	.byte 0xD4, 0x0F, 0xFF
	.byte 0xD4, 0x10, 0x9C
	.byte 0xD4, 0x11, 0x8E # Registers are now reprotected
	.byte 0xD4, 0x12, 0x8F
	.byte 0xD4, 0x13, 0x28
	.byte 0xD4, 0x14, 0x40
	.byte 0xD4, 0x15, 0x96
	.byte 0xD4, 0x16, 0xB9
	.byte 0xD4, 0x17, 0xA3

'''

vga_pal = [0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF]
def gen_pal():
	asm = [
		'initial_palette:',
		'	.byte %s' % ','.join( str(b) for b in vga_pal)
	]
	return '\n'.join(asm)

FIRMWARE_MAIN = r'''
extern void trap_entry();
void firmware_main(){
  uart_init();
  procs_init();
  uart_print("[firmware_main memset proc_list]\n");
  for (int i = %s; i < PROC_TOTAL_COUNT; i++) {
    memset(&proc_list[i], 0, sizeof(proc_list[i]));
    proc_list[i].state = PROC_STATE_NONE;
  }
  active_pid = -1;
  set_timeout(1000); // setup M-mode trap vector
  csrw_mtvec((u64)trap_entry); // enable M-mode timer interrupt  
  csrw_mie(MIE_MTIE);
  csrs_mstatus(MSTAUTS_MIE); // enable MIE in mstatus
  uart_print("[firmware_main waiting...]\n");
  u8 color = 0;
  while(1) {
  	uart_putc('<');
    test_putpixel(color++);
    %s
  	uart_putc('>');
    if(color >= 128) color=0;
  }
}
'''

def gen_firmware(images, strings):
	out = ['void procs_init(){']
	for p,o in enumerate(images):
		out += [
			'struct proc test_proc_%s = {' % p,
			'  .name = "test_proc_%s",' % p,
			'  .pid = %s,' % (p+0),
			'  .hartid = 1,',
			'  .state = PROC_STATE_READY,',
			'  .cpu = {',
			'      .pc = (u64)__proc_entry_%s,' % p,
			'      .x2 = (u64)__proc_%s_stack_top,' % p,
			'  }};',
			'uart_print("[proc_init] proc_list:%s");' % p,
			f'proc_list[{p}] = test_proc_{p};',
		]
	out.append('}')

	out += [
		'void test_putpixel(u8 c){',
		'\n'.join(['putpixel(%s,%s,%s);' %(i,i, i) for i in range(200)]),
	]
	y = 0
	for i in range(320):
		out.append('putpixel(%s,%s,c);' %(i,y))
		if not i%2:
			y += 1
	out.append('}')
	print_meme = ['uart_print("%s");' % m.replace('"', "'") for m in strings]
	out.append(FIRMWARE_MAIN % (len(images), '\n'.join(print_meme) ) )
	return out

def meme(images, strings):
	assert images
	assert strings
	assert len(images) == len(strings)
	out = [ARCH, ARCH_ASM, UART, CPU, TIMER, LIBC]
	out += gen_proc_header(images) + gen_procs(images,strings) + [ INTERRUPTS, TRAP_C ] + gen_firmware(images, strings)
	c = '\n'.join(out)
	print(c)
	tmpld = '/tmp/linker.ld'
	open(tmpld,'wb').write(LINKER_SCRIPT.encode('utf-8'))
	tmps = '/tmp/asm.s'

	asm = [
		START_VGA_S,
		gen_trap_s(),
		'.section .rodata', 
		MODE_13H, gen_pal()
	]
	open(tmps,'wb').write('\n'.join(asm).encode('utf-8'))
	tmp = '/tmp/test.c'
	open(tmp,'wb').write(c.encode('utf-8'))
	cmd = [
		'riscv64-unknown-elf-gcc', '-mcmodel=medany', '-ffreestanding', '-nostdlib', '-nostartfiles', '-nodefaultlibs',
		'-Wl,--no-relax', '-T',tmpld, '-O0', '-g', '-o', '/tmp/test.elf', tmps, tmp
	]
	print(cmd)
	subprocess.check_call(cmd)
	cmd = 'riscv64-unknown-elf-objcopy -O binary -S /tmp/test.elf /tmp/firmware.bin'
	print(cmd)
	subprocess.check_call(cmd.split())
	cmd = 'qemu-system-riscv64 -machine virt -smp 2 -m 2G -serial stdio -bios /tmp/firmware.bin -s -device VGA'
	print(cmd)
	subprocess.check_call(cmd.split())

if __name__ == '__main__':
	images = []; strings = []
	for arg in sys.argv:
		if arg.endswith(('.jpg', '.png', '.gif')) and os.path.isfile(arg):
			c = image2c(arg)
			images.append(c)
		elif arg.endswith(('.', '?', '!')):
			strings.append(arg)

	meme(images, strings)
