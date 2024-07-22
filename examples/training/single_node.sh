python -m torch.distributed.run \
    --nproc_per_node 4 \
    --nnodes 1 \
    --node_rank 0 \
    --master_addr 10.1.1.24 \
    --master_port 14286 \
    ./libs/llama_factory/src/train_bash.py \
    --deepspeed ./src/abstractions/configs/LF_examples/deepspeed/ds_z3_config.json \
    --stage sft \
    --do_train \
    --model_name_or_path /mnt/fl/models/qwen/Qwen1.5-0.5B \
    --dataset alpaca_gpt4_en \
    --dataset_dir ./libs/llama_factory/data \
    --template alpaca \
    --finetuning_type full \
    --output_dir ./output/inference_results/multi_node_trial_run/ \
    --overwrite_cache \
    --overwrite_output_dir \
    --cutoff_len 4096 \
    --preprocessing_num_workers 16 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --gradient_accumulation_steps 1 \
    --lr_scheduler_type polynomial \
    --lr_scheduler_kwargs '{"lr_end": 5e-08, "power": 11}' \
    --logging_steps 5 \
    --warmup_steps 20 \
    --save_steps 100 \
    --eval_steps 100 \
    --evaluation_strategy steps \
    --learning_rate 0.0000150000 \
    --save_total_limit 4 \
    --num_train_epochs 3.0 \
    --max_samples 3000 \
    --val_size 0.1 \
    --ddp_timeout 1800000 \
    --plot_loss \
    --fp16