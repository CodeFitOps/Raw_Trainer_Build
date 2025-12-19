
import sys
import termcolor
import pyfiglet
import string

init_text = "\n>_ RawTrainer init\n\n"
termcolor.cprint(init_text,"magenta", attrs=['bold'])
termcolor.cprint("                                                                    ","white", "on_magenta")
ascii_banner = pyfiglet.figlet_format("      RawTrainer", font="big")
termcolor.cprint(ascii_banner,"magenta", attrs=['bold'])
termcolor.cprint("              ","white", end=' ')
termcolor.cprint("         Engineered by          ","white", "on_magenta")
termcolor.cprint("              ","white", end=' ')
termcolor.cprint("          codeEngTools          ","white", "on_magenta")