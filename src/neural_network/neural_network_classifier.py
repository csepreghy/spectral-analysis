import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import style
import time as time
import datetime
import math

import tensorflow as tf
from tensorflow import keras

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.optimizers import SGD
from tensorflow.keras.callbacks import History, TensorBoard, EarlyStopping, ModelCheckpoint
from tensorflow.keras.layers import Dense, Dropout, Activation, GlobalAveragePooling1D, Flatten, Conv1D, MaxPooling1D, MaxPooling2D, Input, concatenate
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.utils import to_categorical

from .models import create_cnn, create_mlp

from plotify import Plotify


# This is a simple feed forward neural network that uses Keras and Tensorflow.
# Inputs:
#    - df: pandas dataframe with training data
#    - batch_size: batch size (integer)
#    - hidden_layers: an array of numbers that represent the number of hidden layers and the 
#                     number of neurons in each. [128, 128, 128] is 3 hidden layers with 128 
#                     neurons each
#    - n_ephoch: the number of epochs the system trains
#
# It then prepares, trains and saves the model to disk so you can load it later. Currently it is 
# a binary classifier, but it can be easily changed
# It also automatically scales the data. This should speed up the process of training

def prepare_data(df):
  print('df', df)
  columns = []

  df['class'] = pd.Categorical(df['class'])
  df_dummies = pd.get_dummies(df['class'], prefix='category')
  df = pd.concat([df, df_dummies], axis=1)
  df_spectra = df[['flux_list']]
  df_source_info = df.drop(columns={'flux_list'})

  for column in df_source_info.columns:
    if column not in ['class', 'dec', 'ra', 'plate', 'wavelength', 'objid', 'subClass']:
      columns.append(column)

  X_source_info = []
  X_spectra = []
  y = []

  for index, spectrum in df_source_info[columns].iterrows():
    X_row = []

    # adding the spectral lines
    spectral_lines = spectrum['spectral_lines']

    # spectral lines are sometimes missing
    if type(spectral_lines) == list:
      for spectral_line in spectral_lines:
        X_row.append(spectral_line)

    elif math.isnan(spectral_lines):
      spectral_lines = [-99] * 14 # number of spectral lines is 14
  
      for spectral_line in spectral_lines:
          X_row.append(spectral_line)

    X_row.append(spectrum['z'])
    X_row.append(spectrum['zErr'])
    X_row.append(spectrum['petroMag_u'])
    X_row.append(spectrum['petroMag_g'])
    X_row.append(spectrum['petroMag_r'])
    X_row.append(spectrum['petroMag_i'])
    X_row.append(spectrum['petroMag_z'])
    X_row.append(spectrum['petroMagErr_u'])
    X_row.append(spectrum['petroMagErr_g'])
    X_row.append(spectrum['petroMagErr_r'])
    X_row.append(spectrum['petroMagErr_i'])
    X_row.append(spectrum['petroMagErr_z'])

    category_GALAXY = spectrum['category_GALAXY']
    category_QSO = spectrum['category_QSO']
    category_STAR = spectrum['category_STAR']

    y_row = [category_GALAXY, category_QSO, category_STAR]

    X_source_info.append(X_row)
    y.append(y_row)
  
  for _, spectrum in df_spectra.iterrows():
    X_row = []
    
    flux_list = spectrum['flux_list']
    
    for flux in flux_list:
      X_row.append(flux)
    
    X_spectra.append(X_row)
  
  return X_source_info, X_spectra, y



def run_neural_network(df, config):
  n_classes = 3
  X_source_info, X_spectra, y = prepare_data(df)
  #meta-data
  #continuum
  X_train_source_info, X_test_source_info, y_train, y_test = train_test_split(X_source_info, y, test_size=0.2)
  X_train_source_info, X_val_source_info, y_train, y_val = train_test_split(X_train_source_info, y_train, test_size=0.2)

  X_train_spectra, X_test_spectra = train_test_split(X_spectra, None, test_size=0.2)
  X_train_spectra, X_val_spectra = train_test_split(X_train_spectra, None, test_size=0.2)

  scaler = StandardScaler()

  X_train_source_info = scaler.fit_transform(X_train_source_info)
  X_test_source_info = scaler.transform(X_test_source_info)
  X_val_source_info = scaler.transform(X_val_source_info)

  X_train_spectra = scaler.fit_transform(X_train_spectra)
  X_test_spectra = scaler.transform(X_test_spectra)
  X_val_spectra = scaler.transform(X_val_spectra)

  X_train_spectra = np.expand_dims(X_train_spectra, axis=2)
  X_test_spectra = np.expand_dims(X_test_spectra, axis=2)

  y_train = np.array(y_train)
  y_test = np.array(y_test)

  cnn = create_cnn(input_length=X_train_spectra.shape[1])
  mlp = create_mlp(input_shape=X_train_source_info.shape[1])
  



  # combine the output of the two branches
  combined = concatenate([cnn.output, mlp.output])

  # apply a fully connected layer for last classification
  final_classifier = Dense(128, activation="relu")(combined)
  final_classifier = Dense(n_classes, activation="softmax")(final_classifier)
  
  model = Model(inputs=[mlp.input, cnn.input], outputs=final_classifier)

  model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

  tensorboard = TensorBoard(log_dir='logs/{}'.format('cnn-mlp_{}'.format(time.time())))
  earlystopping = EarlyStopping(monitor='val_accuracy', patience=2)
  modelcheckpoint = ModelCheckpoint(filepath='best_model_epoch.{epoch:02d}-{val_loss:.2f}.h5', monitor='val_loss', save_best_only=True),

  callbacks_list = [
    # modelcheckpoint,
    # earlystopping,
    tensorboard
  ]

  history = model.fit(x=[X_train_source_info, X_train_spectra],
                      y=y_train,
                      validation_data=([X_test_source_info, X_test_spectra], y_test),
                      epochs=50,
                      callbacks=callbacks_list)


  # evaluate the model
  _, train_acc = model.evaluate([X_train_source_info, X_train_spectra], y_train, verbose=0)
  _, test_acc = model.evaluate([X_test_source_info, X_test_spectra], y_test, verbose=0)


  print('Train: %.3f, Test: %.3f' % (train_acc, test_acc))
  # plot loss during training
  plt.subplot(211)
  plt.title('Loss')
  plt.plot(history.history['loss'], label='train')
  plt.plot(history.history['val_loss'], label='test')
  plt.legend()
  # plot accuracy during training
  plt.subplot(212)
  plt.title('Accuracy')

  plt.plot(history.history['accuracy'], label='train')
  plt.plot(history.history['val_accuracy'], label='test')
  plt.legend()
  plt.show()

  return cnn

def train_test_split(X, y, test_size):
  if y is not None and len(X) != len(y): print('X and y does not have the same length')
  
  n_test = round(len(X) * test_size)
  n_train = len(X) - n_test
  
  X_test = X[-n_test:]
  X_train = X[:n_train]

  print('len(X_train', len(X_train))

  # print('type(X_test', type(X_test))

  if y is not None:
    y_test = y[-n_test:]
    y_train = y[:n_train]

  if y is not None:
    return X_train, X_test, y_train, y_test
  
  else:
    return X_train, X_test
  
def summarize_results():
  print('hello')

def evaluate_model():
  print('hello')


# def run_cnn(df, config)