#!/usr/bin/env python3
# Figma to baremetal RISCV: by Brent Hartshorn
# install: sudo apt-get install gcc-riscv64-unknown-elf qemu-system-riscv64

import os, sys, subprocess, json, string
from PIL import Image, ImageFont, ImageDraw

TEST = 'https://www.figma.com/design/J9oh3PpkkivuV5xp5p5go9/Untitled?node-id=0-1&t=19PvBbLLyJstPZBs-1'
TOKEN = 'figd_pt53oO8QXO7v2YwYF4CNxo4sHMznjb9PJ6P4UpXq'


## https://github.com/Amatobahn/FigmaPy
if not os.path.isdir('./FigmaPy'):
	cmd = ['git', 'clone', '--depth', '1', 'https://github.com/Amatobahn/FigmaPy.git']
	subprocess.check_call(cmd)

assert os.path.isdir('./FigmaPy')
sys.path.append('./FigmaPy')
import figmapy
print(figmapy)

LIB_DRAW = '''
void draw_hline(int x, int y, int w, int color){
	for (int i=x; i<w; i++) putpixel(i,y,color);
}
void draw_fill(int x, int y, int w, int h, int color){
	for (int yi=0; yi<h; yi++){
		draw_hline(x, y+yi, w, color);
	}
}
'''

def gen_font( size=10):
	ascii = {}
	out = []
	for c in string.ascii_letters + string.digits + string.punctuation:
		img = Image.new(('RGB'), (size,size))
		draw = ImageDraw.Draw(img)
		draw.text((0,0), c)
		#img = img.convert('P')
		ascii[c] = o = ['void draw_char_%s(int x, int y, int color){	//%s' % (ord(c),c) ]
		#for pidx, pixel in enumerate(img.getdata()):
		for y in range(size):
			for x in range(size):
				r,g,b = img.getpixel((x,y))
				if r:
					o.append('	putpixel(%s+x,%s+y,color);' %(x,y))

		o.append('}')
		out += o
	return '\n'.join(out)

LIB_FONT = gen_font()


vga_pal = [0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF]
def to_vga_color( clr ):
	r = int(clr['r'] * 255)
	g = int(clr['g'] * 255)
	b = int(clr['b'] * 255)
	score = None
	color = None
	idx = 0
	for i in range(0, len(vga_pal), 3):
		vr = vga_pal[i]
		vg = vga_pal[i]
		vb = vga_pal[i]
		diff = abs(r-vr) + abs(g-vg) + abs(b-vb)
		if color is None or diff < score:
			score = diff
			color = idx
		idx += 1
	return color

def id2c(id):
	return id.replace(':', '_')

def meta_to_metal( meta ):
	c = [LIB_DRAW, LIB_FONT]
	print(meta)

	c += [
		'void redraw_background(){',
		'	draw_fill(0,0, 320, 240, %s);' % to_vga_color(meta['bgcolor']),
		'}',
	]

	funcs = ['redraw_background']

	for elt in meta['frames']:
		x = int(elt['x'])
		y = int(elt['y'])
		w = int(elt['w'])
		h = int(elt['h'])

		funcs.append('redraw_%s' % id2c(elt['id']))

		c += [
			'void redraw_%s(){' % id2c(elt['id']),
		]
		if elt['type']=='TEXT':
			c.append('//printf("%s")' % elt['text'])
			for aidx, a in enumerate(elt['text']):
				if a == ' ':
					continue
				cx = aidx * 10
				cx += x
				c.append('	draw_char_%s(%s,%s,100);' % (ord(a), cx, y) )
		else:
			if elt['fill']:
				color = to_vga_color(elt['fill'])
				c.append('	draw_fill(%s,%s, %s,%s, %s);' % (x,y, w,h, color))

			if elt['stroke']:
				color = to_vga_color(elt['stroke'])
				c.append('	draw_hline(%s,%s, %s, %s);' % (x,y, w, color))
				c.append('	draw_hline(%s,%s, %s, %s);' % (x,y+h, w, color))

		c.append('}')

	c += [
		'void firmware_main(){',
		'	while (1) {',
	]
	for f in funcs:
		c.append( '	%s();' %f )

	if '--mouse' in sys.argv:
		c += [
			'	int x = debug_get_mouse(0);',
			'	int y = debug_get_mouse(1);',
			'	putpixel(x,y,100);',
			'	putpixel(x+1,y+1,10);',
			'	putpixel(x+2,y+2,32);',
		]
	c.append('	}')
	c.append('}')

	return '\n'.join(c)

def figma_to_meta(file_key):
	frames = []
	pngs = []
	ids = []
	meta = {'frames':frames, 'pngs':pngs, 'ids':ids}

	if figmapy is None:
		return ''
	if file_key.startswith('https://www.figma.com/file/'):
		file_key = file_key[len('https://www.figma.com/file/') : ]
	elif file_key.startswith('https://www.figma.com/design/'):
		file_key = file_key[len('https://www.figma.com/design/') : ]
	if '/' in file_key:
		file_key = file_key.split('/')[0]

	print(file_key)
	fig = figmapy.FigmaPy(token=TOKEN)
	print(fig)

	file = fig.get_file(key=file_key)
	if not file: raise RuntimeError('invalid file key: %s' % file_key)
	print(file)
	print([x.name for x in file.document.children])


	page1 = file.document.children[0]
	meta['bgcolor'] = page1.backgroundColor
	nodes = {}
	css = {}
	minx = None
	miny = None
	for n in page1.children:
		x = n.absoluteRenderBounds['x']
		y = n.absoluteRenderBounds['y']
		if minx is None or x < minx:
			minx = x
		if miny is None or y < miny:
			miny = y

	print('minx:', minx)
	print('miny:', miny)

	for n in page1.children:
		ids.append(n.id)
		print(n.name)
		print(n.type)
		print('isFixed', n.isFixed)
		print('layoutAlign', n.layoutAlign)
		print('size', n.size)
		print('strokeWeight', n.strokeWeight)
		print('styles', n.styles)
		print('fills', n.fills)
		print('strokes', n.strokes)

		x = n.absoluteBoundingBox.x
		y = n.absoluteBoundingBox.y
		w = n.absoluteBoundingBox.width
		h = n.absoluteBoundingBox.height
		print('bounding box: %s %s %s %s'  %(x,y,w,h))
		x = n.absoluteRenderBounds['x']
		y = n.absoluteRenderBounds['y']
		w = n.absoluteRenderBounds['width']
		h = n.absoluteRenderBounds['height']
		print('render: %s %s %s %s'  %(x,y,w,h))

		x, y = (x+abs(minx), y+abs(miny))
		print('abs x y:', x,y)

		elt = {
			'type':n.type,
			'id': n.id,
			'strokeWeight':n.strokeWeight,
			'x': x, 'y':y,
			'w': w, 'h':h,
			'stroke':None,
			'fill'  :None,
		}
		frames.append(elt)

		if n.fills:
			for f in n.fills:
				elt['fill'] = f.color  ## this is a dict

		if n.strokes:
			for s in n.strokes:
				elt['stroke'] = s.color

		if n.type=="TEXT":
			elt['text'] = n.characters

	return meta

QEMU_CUSTOM = './qemu/build/qemu-system-riscv64'
if not os.path.isdir('./qemu') and '--mouse' in sys.argv:
	cmd = ['git', 'clone', '--depth', '1', 'https://github.com/brentharts/qemu.git']
	subprocess.check_call(cmd)

MOUSE_C = '''
int debug_get_mouse(u32 idx){
	u32 *ptr = (volatile u32*)0x11000;
	return ptr[idx];
}
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

ARCH_ASM = '''
#define readu8(addr) (*(const u8 *)(addr))
#define readu16(addr) (*(const u16 *)(addr))
#define readu32(addr) (*(const u32 *)(addr))
#define readu64(addr) (*(const u64 *)(addr))
#define writeu8(addr, val) (*(u8 *)(addr) = (val))
#define writeu16(addr, val) (*(u16 *)(addr) = (val))
#define writeu32(addr, val) (*(u32 *)(addr) = (val))
#define writeu64(addr, val) (*(u64 *)(addr) = (val))

//GOTCHA::BREAKS-ASM-PARSER//static inline void csrw_mtvec(const volatile u64 val) { asm volatile("csrw mtvec, %0" :: "r"(val)); } // note the space
static inline void csrw_mtvec(const volatile u64 val) { asm volatile("csrw mtvec,%0" :: "r"(val)); }
static inline void csrw_mie(const volatile u64 val) { asm volatile("csrw mie,%0" :: "r"(val)); }
static inline void csrs_mstatus(const volatile u64 val) { asm volatile("csrs mstatus,%0" :: "r"(val)); }
static inline u64 csrr_mcause(){
  volatile u64 val;
  asm volatile("csrr %0,mcause" : "=r"(val) :);
  return val;
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
	.byte 0xD4, 0x12, 0x8F, 0xD4, 0x13, 0x28, 0xD4, 0x14, 0x40, 0xD4, 0x15, 0x96, 0xD4, 0x16, 0xB9, 0xD4, 0x17, 0xA3

'''

vga_pal = [0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF,0x00, 0x00, 0x00,0x00, 0x00, 0x55,0x00, 0x00, 0xAA,0x00, 0x00, 0xFF,0x00, 0x55, 0x00,0x00, 0x55, 0x55,0x00, 0x55, 0xAA,0x00, 0x55, 0xFF,0x00, 0xAA, 0x00,0x00, 0xAA, 0x55,0x00, 0xAA, 0xAA,0x00, 0xAA, 0xFF,0x00, 0xFF, 0x00,0x00, 0xFF, 0x55,0x00, 0xFF, 0xAA,0x00, 0xFF, 0xFF,0x55, 0x00, 0x00,0x55, 0x00, 0x55,0x55, 0x00, 0xAA,0x55, 0x00, 0xFF,0x55, 0x55, 0x00,0x55, 0x55, 0x55,0x55, 0x55, 0xAA,0x55, 0x55, 0xFF,0x55, 0xAA, 0x00,0x55, 0xAA, 0x55,0x55, 0xAA, 0xAA,0x55, 0xAA, 0xFF,0x55, 0xFF, 0x00,0x55, 0xFF, 0x55,0x55, 0xFF, 0xAA,0x55, 0xFF, 0xFF,0xAA, 0x00, 0x00,0xAA, 0x00, 0x55,0xAA, 0x00, 0xAA,0xAA, 0x00, 0xFF,0xAA, 0x55, 0x00,0xAA, 0x55, 0x55,0xAA, 0x55, 0xAA,0xAA, 0x55, 0xFF,0xAA, 0xAA, 0x00,0xAA, 0xAA, 0x55,0xAA, 0xAA, 0xAA,0xAA, 0xAA, 0xFF,0xAA, 0xFF, 0x00,0xAA, 0xFF, 0x55,0xAA, 0xFF, 0xAA,0xAA, 0xFF, 0xFF,0xFF, 0x00, 0x00,0xFF, 0x00, 0x55,0xFF, 0x00, 0xAA,0xFF, 0x00, 0xFF,0xFF, 0x55, 0x00,0xFF, 0x55, 0x55,0xFF, 0x55, 0xAA,0xFF, 0x55, 0xFF,0xFF, 0xAA, 0x00,0xFF, 0xAA, 0x55,0xFF, 0xAA, 0xAA,0xFF, 0xAA, 0xFF,0xFF, 0xFF, 0x00,0xFF, 0xFF, 0x55,0xFF, 0xFF, 0xAA,0xFF, 0xFF, 0xFF]
def gen_pal():
	asm = [
		'initial_palette:',
		'	.byte %s' % ','.join( str(b) for b in vga_pal)
	]
	return '\n'.join(asm)

def make(c):
	out = [ARCH, ARCH_ASM, LIBC]
	if '--mouse' in sys.argv: out.append(MOUSE_C)
	out.append(c)
	c = '\n'.join(out)
	tmpc = '/tmp/figma.c'
	open(tmpc, 'wb').write(c.encode('utf-8'))
	tmpld = '/tmp/linker.ld'
	open(tmpld,'wb').write(LINKER_SCRIPT.encode('utf-8'))
	tmps = '/tmp/asm.s'

	asm = [
		START_VGA_S,
		'.section .rodata', 
		MODE_13H, gen_pal()
	]
	ob = asm2o('\n'.join(asm))

	elf = '/tmp/test.elf'
	cmd = [
		'riscv64-unknown-elf-gcc', '-mcmodel=medany', '-ffunction-sections',
		'-ffreestanding', '-nostdlib', '-nostartfiles', '-nodefaultlibs',
		'-Wl,--no-relax', '-T',tmpld, '-O0', '-g', '-o', elf, ob, tmpc,
	]
	print(cmd)
	subprocess.check_call(cmd)

	if '--mouse' in sys.argv:
		cmd = 'riscv64-unknown-elf-objcopy -O binary -S %s /tmp/firmware.bin' % elf
		print(cmd)
		if not os.path.isfile(QEMU_CUSTOM):
			os.system('cd ./qemu && python3 qemu.py --build')
		else:
			cmd = [QEMU_CUSTOM]
			cmd += '-machine virt -m 256M -serial stdio -device VGA -bios /tmp/firmware.bin'.split()
			print(cmd)
			subprocess.check_call(cmd)

	else:
		cmd = 'riscv64-unknown-elf-objcopy -O binary -S %s /tmp/firmware.bin' % elf
		print(cmd)
		subprocess.check_call(cmd.split())
		cmd = 'qemu-system-riscv64 -machine virt -smp 2 -m 2G -serial stdio -bios /tmp/firmware.bin -s -device VGA'
		print(cmd)
		subprocess.check_call(cmd.split())
	return elf

def asm2o(s, name='asm2o'):
	asm = '/tmp/asm2o.s'
	open(asm,'wb').write(s.encode('utf-8'))
	o = '/tmp/%s.o' % name
	cmd = [ 'riscv64-unknown-elf-as', '-g', '-o',o, asm]
	print(cmd)
	subprocess.check_call(cmd)
	return o

if __name__=='__main__':
	tmp = '/tmp/figma-cache.json'
	if '--offline' in sys.argv:
		m = json.loads( open(tmp, 'rb').read() )
	else:
		url = TEST
		for arg in sys.argv:
			if arg.startswith('https://www.figma.com/'):
				url = arg
			elif arg.startswith('figd_'):
				TOKEN = arg
		m = figma_to_meta(url)
		open(tmp, 'wb').write(json.dumps(m).encode('utf-8'))

	c = meta_to_metal(m)
	print(c)
	make(c)
