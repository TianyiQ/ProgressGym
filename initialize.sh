export PYTHONNOUSERSITE=1
CONDA_OVERRIDE_CUDA=12.1 conda env create -y --file ./src/config/conda-recipe.yaml -n pa38
conda create --name pa38-lf --clone pa38
conda activate pa38-lf
conda run --no-capture-output -n pa38-lf pip3 install -r ./libs/llama_factory/requirements.txt
conda run --no-capture-output -n pa38-lf pip3 install "transformers>=4.40.2" "triton>=2.0.0"
conda activate pa38
conda run --no-capture-output -n pa38 pip3 install -r ./src/config/requirements-pip.txt
conda run --no-capture-output -n pa38 pip3 install -r ./libs/moralchoice/requirements.txt
conda remove --force -y pyarrow
conda run --no-capture-output -n pa38 pip3 uninstall -y pyarrow
conda run --no-capture-output -n pa38 pip3 install pyarrow
conda run --no-capture-output -n pa38 pip3 install -U vllm

# if seeing --multinode, then we are in a multi-node setup and need to install further dependencies
if [ "$1" == "--multinode" ]; then
    . ./src/abstractions/configs/multinode/deepspeed_prep.sh
    . ./src/abstractions/configs/multinode/create_multinode_env.sh
fi

sudo apt-get install -y libyajl-dev
sudo apt-get install -y lynx