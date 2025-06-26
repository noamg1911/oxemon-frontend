define _check-var
	@if [ -z "$($1)" ]; then \
		echo "❌ ERROR: Missing required argument: $1=<value>"; \
		exit 1; \
	fi
endef

build:
	docker-compose pull
	docker-compose build --pull

start:
	$(call _check-var,CONFIG_FOLDER)
	docker-compose up -d

stop:
	docker-compose down

.PHONY: config
config:
	$(call _check-var,metrics)
	$(call _check-var,dictionary)
	$(call _check-var,output)
	python3 utils/configure.py --dictionary=$(dictionary) --metrics=$(metrics) --output=$(output)
