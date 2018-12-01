clean:
	rm -rf build dist *.egg-info

venv:
	pipenv shell

venv-init:
	pipenv install -d
	pipenv shell

pypi: clean
	python setup.py sdist
	twine upload dist/*

pypi-test: clean
	python setup.py sdist
	twine upload dist/* -r pypitest

install:
	pip install .

install-pypi:
	pip install --index-url https://pypi.python.org/pypi spiderkeeper-deploy

install-pypi-test:
	pip install --index-url https://test.pypi.org/simple spiderkeeper-deploy
