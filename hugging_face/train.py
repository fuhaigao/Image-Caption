import math
import json
import pandas as pd
import os

from transformers import DataCollatorForLanguageModeling
from transformers import RobertaConfig
from transformers import RobertaForMaskedLM # RobertaLM for learning
from transformers import RobertaTokenizerFast # After training tokenizern we will wrap it so it can be used by Roberta model
from transformers import Seq2SeqTrainer
from transformers import Seq2SeqTrainingArguments
from transformers import Trainer, TrainingArguments

import dataset

TRAIN_BATCH_SIZE = 20   # input batch size for training (default: 64)
VALID_BATCH_SIZE = 5   # input batch size for testing (default: 1000)
VAL_EPOCHS = 1 
LEARNING_RATE = 1e-4    # learning rate (default: 0.01)
SEED = 42               # random seed (default: 42)
MAX_LEN = 128           # Max length for product description
SUMMARY_LEN = 20         # Max length for product names

TRAIN_EPOCHS = 2       # number of epochs to train (default: 10)
WEIGHT_DECAY = 0.01
SEED = 42               # random seed (default: 42)
MAX_LEN = 128
SUMMARY_LEN = 20   # Maximum length of caption generated by the model


def train():
    df = generate_df()
    data = df["captions"]
    # Removing the end of line character \n
    data = data.replace("\n"," ")
    # Set the ID to 0
    prefix=0
    # Create a file for every description value
    prefix = column_to_files(data, prefix)

    # load trained tokenizer
    tokenizer = RobertaTokenizerFast.from_pretrained('Byte_tokenizer', max_len=MAX_LEN)

    model = RobertaForMaskedLM(
        config=RobertaConfig(
            vocab_size=10000,
            max_position_embeddings=514,
            num_attention_heads=12,
            num_hidden_layers=6,
            type_vocab_size=1,
        )
    )

    # Define the Data Collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm=True, mlm_probability=0.15
    )

    # Create the train and evaluation dataset
    train_dataset = dataset.CustomDataset(df['captions'][:38000], tokenizer)
    eval_dataset = dataset.CustomDataset(df['captions'][38000:], tokenizer)

    model_folder = "RobertaMLM"
    # Define the training arguments
    training_args = TrainingArguments(
        output_dir=model_folder,
        overwrite_output_dir=True,
        evaluation_strategy = 'epoch',
        num_train_epochs=TRAIN_EPOCHS,
        learning_rate=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        per_device_train_batch_size=TRAIN_BATCH_SIZE,
        per_device_eval_batch_size=VALID_BATCH_SIZE,
        save_steps=8192,
        #eval_steps=4096,
        save_total_limit=1,
    )
    # Create the trainer for our model
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        #prediction_loss_only=True,
    )

    # Train the model
    trainer.train()

    eval_results = trainer.evaluate()

    print(f"Perplexity: {math.exp(eval_results['eval_loss']):.2f}")
    tokenizer.save_pretrained('Byte_tokenizer')
    trainer.save_model(model_folder)


def generate_df():

    # with open('../data/anticipated_dataset.json', 'r') as openfile:
    with open('data.json', 'r') as openfile:
        json_object = json.load(openfile)

    images_caption_dict = dict(json_object)


    df = pd.DataFrame([])

    captions = []
    images = []
    for image in list(images_caption_dict.keys()):
        caption = images_caption_dict[image]
        # captions.append(('.'.join([ sent.rstrip() for sent in ('.'.join(caption)).split('<e>.<s>')]))\
        #                         .replace('<s> ','').replace('  <e>','.'))
        for capt in caption:
            captions.append(capt.replace('<s> ','').replace('  <e>','').strip())
            images.append(image)
            
    df['images'] = images
    df['captions'] = captions
    return df

def column_to_files(column, prefix, txt_files_dir = "./text_split"):
    # The prefix is a unique ID to avoid to overwrite a text file
    i=prefix
    #For every value in the df, with just one column
    for row in column.to_list():
      # Create the filename using the prefix ID
        file_name = os.path.join(txt_files_dir, str(i)+'.txt')
        try:
            # Create the file and write the column text to it
            f = open(file_name, 'wb')
            f.write(row.encode('utf-8'))
            f.close()
        except Exception as e:  #catch exceptions(for eg. empty rows)
            print(row, e) 
        i+=1
    # Return the last ID
    return i

if __name__ == '__main__':
    train()