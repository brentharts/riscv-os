#include "riscv_asm.h"
#include "uart.h"
#include "timer.h"

void trap_entry();

void echo()
{
  uart_print("Hello, RISC-V!\n");
  uart_print("echo> ");
  for (;;)
  {
    u32 data = uart_getc();
    if (!(data & UART_RXFIFO_EMPTY))
    {
      uart_putc(data & UART_RXFIFO_DATA);
    }
  }
}

void trap_init()
{
  csrw_mtvec((u64)trap_entry);
}

void firmware_main()
{
  trap_init();
  uart_init();
  // ecall();
  // echo();
  while (1)
  {
    for (u32 i = 0; i < 10000000; i++)
    {
    }
    uart_print_int(mtime());
    uart_print("\n");
  }
  
}