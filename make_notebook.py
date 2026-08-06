import nbformat as nbf

nb = nbf.v4.new_notebook()

nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    },
    "language_info": {
        "codemirror_mode": {
            "name": "ipython",
            "version": 3
        },
        "file_extension": ".py",
        "mimetype": "text/x-python",
        "name": "python",
        "nbconvert_exporter": "python",
        "pygments_lexer": "ipython3",
        "version": "3.10.12"
    }
}

cell1 = nbf.v4.new_code_cell("!pip install kaggle-environments stable-baselines3")

with open("heuristic.py", "r") as f:
    main_content = f.read()
cell2 = nbf.v4.new_code_cell("%%writefile heuristic.py\n" + main_content)

with open("env_wrapper.py", "r") as f:
    env_content = f.read()
cell3 = nbf.v4.new_code_cell("%%writefile env_wrapper.py\n" + env_content)

with open("train_rl.py", "r") as f:
    train_content = f.read()
cell4 = nbf.v4.new_code_cell("%%writefile train_rl.py\n" + train_content)

run_cell = nbf.v4.new_code_cell("!python train_rl.py --steps 2000000")

nb.cells = [cell1, cell2, cell3, cell4, run_cell]
with open("train_on_kaggle.ipynb", "w") as f:
    nbf.write(nb, f)
print("Created fixed train_on_kaggle.ipynb with metadata")
