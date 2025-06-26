build:
	docker-compose pull
	docker-compose build --pull

start:
	docker-compose up

stop:
	docker-compose down


_check-vars:
	@$(foreach var,metrics dictionary output, \
		if [ -z "$($(var))" ]; then \
			echo "❌ ERROR: Missing required argument: $(var)=<value>"; \
			exit 1; \
		fi; \
	)

.PHONY: config
config: _check-vars
	python3 utils/configure.py --dictionary=$(dictionary) --metrics=$(metrics) --output=$(output)
