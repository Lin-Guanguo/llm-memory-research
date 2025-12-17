.PHONY: install add search list clear help

# Default target
help:
	@echo "Usage:"
	@echo "  make install           Install dependencies"
	@echo "  make add PATH=<path>   Add a file or directory to knowledge base"
	@echo "  make search Q=<query>  Search the knowledge base"
	@echo "  make list              List all memories"
	@echo "  make clear             Clear all memories"
	@echo ""
	@echo "Examples:"
	@echo "  make add PATH=~/notes/meeting.md"
	@echo "  make add PATH=~/notes/           # Add all .txt/.md files in directory"
	@echo "  make search Q=\"what did I do today\""
	@echo "  make list"

install:
	pip install -r requirements.txt

add:
ifndef PATH
	$(error PATH is required. Usage: make add PATH=path/to/file_or_dir)
endif
	python main.py add "$(PATH)" -v

search:
ifndef Q
	$(error Q is required. Usage: make search Q="your query")
endif
	python main.py search "$(Q)"

list:
	python main.py list

clear:
	python main.py clear -f
