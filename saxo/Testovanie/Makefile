# Forwarder Makefile: umožní spúšťať ciele z root Makefile aj z tohto priečinka

# Pokus sa nájsť root repozitára cez git; fallback na relatívnu cestu (5x ..)
ROOT ?= $(shell git -C $(CURDIR) rev-parse --show-toplevel 2>/dev/null)
ifeq ($(strip $(ROOT)),)
ROOT := $(abspath $(CURDIR)/../../../../../)
endif

.PHONY: _forward

# Zachytí akýkoľvek cieľ a presmeruje ho do root Makefile
.DEFAULT: _forward
	@$(MAKE) -C $(ROOT) $(MAKECMDGOALS)
