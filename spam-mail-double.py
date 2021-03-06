# -*- coding=utf-8 -*-
from sklearn.feature_extraction.text import CountVectorizer
import os
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import train_test_split
from sklearn import metrics
import matplotlib.pyplot as plt
import numpy as np
from sklearn import svm
from sklearn.feature_extraction.text import TfidfTransformer
import cPickle as pickle
import tensorflow as tf
import tflearn
from tflearn.layers.core import input_data, dropout, fully_connected
from tflearn.layers.conv import conv_1d, global_max_pool
from tflearn.layers.conv import conv_2d, max_pool_2d
from tflearn.layers.merge_ops import merge
from tflearn.layers.estimator import regression
from tflearn.data_utils import to_categorical, pad_sequences
from sklearn.neural_network import MLPClassifier
from tflearn.layers.normalization import local_response_normalization
from tensorflow.contrib import learn
from sklearn import metrics

max_features=5000
max_document_length=100

data_pkl_file="data-spam-mail.pkl"
label_pkl_file="label-spam-mail.pkl"

def load_one_file(filename):
    x=""
    with open(filename) as f:
        for line in f:
            line=line.strip('\n')
            line = line.strip('\r')
            x+=line
    return x

def load_files_from_dir(rootdir):
    x=[]
    list = os.listdir(rootdir)
    for i in range(0, len(list)):
        path = os.path.join(rootdir, list[i])
        if os.path.isfile(path):
            v=load_one_file(path)
            x.append(v)
    return x

def load_all_files():
    ham=[]
    spam=[]
    for i in range(1,2):
        path="../data/mail/enron%d/ham/" % i
        print "Load %s" % path
        ham+=load_files_from_dir(path)
        path="../data/mail/enron%d/spam/" % i
        print "Load %s" % path
        spam+=load_files_from_dir(path)
    return ham,spam

def get_features_by_wordbag():
    ham, spam=load_all_files()
    x=ham+spam
    y=[0]*len(ham)+[1]*len(spam)
    vectorizer = CountVectorizer(
                                 decode_error='ignore',
                                 strip_accents='ascii',
                                 max_features=max_features,
                                 stop_words='english',
                                 max_df=1.0,
                                 min_df=1 )
    print vectorizer
    x=vectorizer.fit_transform(x)
    x=x.toarray()
    return x,y

def show_diffrent_max_features():
    global max_features
    a=[]
    b=[]
    for i in range(1000,20000,2000):
        max_features=i
        print "max_features=%d" % i
        x, y = get_features_by_wordbag()
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.4, random_state=0)
        gnb = GaussianNB()
        gnb.fit(x_train, y_train)
        y_pred = gnb.predict(x_test)
        score=metrics.accuracy_score(y_test, y_pred)
        a.append(max_features)
        b.append(score)
        plt.plot(a, b, 'r')
    plt.xlabel("max_features")
    plt.ylabel("metrics.accuracy_score")
    plt.title("metrics.accuracy_score VS max_features")
    plt.legend()
    plt.show()

##2-gram+tfidf
def get_features_by_2gram_tfidf():

    if os.path.exists(data_pkl_file) and os.path.exists(label_pkl_file):
        f = open(data_pkl_file, 'rb')
        x = pickle.load(f)
        f.close()
        f = open(label_pkl_file, 'rb')
        y = pickle.load(f)
        f.close()
    else:
        ham, spam=load_all_files()
        x=ham+spam
        y=[0]*len(ham)+[1]*len(spam)

    CV = CountVectorizer(ngram_range=(2, 2), decode_error="ignore",max_features=max_features,
                                       token_pattern = r'\b\w+\b',min_df=1, max_df=1.0)
    x=CV.fit_transform(x).toarray()
    transformer = TfidfTransformer(smooth_idf=False)
    print transformer
    tfidf = transformer.fit_transform(x)
    x = tfidf.toarray()
    return  x,y

##双层卷积
def do_dccnn(trainX, testX, trainY, testY):
    global max_document_length
    print "Double Convolution CNN "
    y = trainY+testY
    y_test = testY
    max_sequence = len(y)

    trainX = pad_sequences(trainX, maxlen=max_document_length, value=0.)
    testX = pad_sequences(testX, maxlen=max_document_length, value=0.)
    # Converting labels to binary vectors
    trainY = to_categorical(trainY, nb_classes=2)
    testY = to_categorical(testY, nb_classes=2)
    

    # Building convolutional network
    network = input_data(shape=[None,max_document_length], name='input')
    network = tflearn.embedding(network, input_dim=max_sequence+1, output_dim=128)

    branch11 = conv_1d(network, 128, 3, padding='valid', activation='relu', regularizer="L2")
    branch12 = conv_1d(network, 128, 4, padding='valid', activation='relu', regularizer="L2")
    branch13 = conv_1d(network, 128, 5, padding='valid', activation='relu', regularizer="L2")
    #print branch11.shape
    #network = merge([branch11, branch12, branch13], mode='concat', axis=1)
    #network = tf.expand_dims(network, 2)
    #network = global_max_pool(network)

    branch21 = conv_1d(branch11, 128, 3, padding='valid', activation='relu', regularizer="L2")
    branch22 = conv_1d(branch12, 128, 4, padding='valid', activation='relu', regularizer="L2")
    branch23 = conv_1d(branch13, 128, 5, padding='valid', activation='relu', regularizer="L2")
    print branch21.shape
    
    network = merge([branch21, branch22, branch23], mode='concat', axis=1)
    network = tf.expand_dims(network, 2)
    network = global_max_pool(network)
    network = dropout(network, 0.4)
    network = fully_connected(network, 2, activation='softmax')
    network = regression(network, optimizer='adam', learning_rate=0.001,
                         loss='categorical_crossentropy', name='target')
    # Training
    model = tflearn.DNN(network, tensorboard_verbose=0)
    model.fit(trainX, trainY,
              n_epoch=2, shuffle=True, validation_set=(testX, testY),
              show_metric=True, batch_size=100,run_id="spam")
    
    y_predict_list = model.predict(testX)
    y_predict=[]
    for i in y_predict_list:
        if i[0] > 0.5:
            y_predict.append(0)
        else:
            y_predict.append(1)
    print 'y_predict_list:'
    print y_predict_list
    print 'y_predict:'
    print  y_predict
    print y_test
    do_metrics(y_test,y_predict)

def do_cnn_wordbag(trainX, testX, trainY, testY):
    global max_document_length
    print "CNN and tf"

    trainX = pad_sequences(trainX, maxlen=max_document_length, value=0.)
    testX = pad_sequences(testX, maxlen=max_document_length, value=0.)
    # Converting labels to binary vectors
    trainY = to_categorical(trainY, nb_classes=2)
    testY = to_categorical(testY, nb_classes=2)

    # Building convolutional network
    network = input_data(shape=[None,max_document_length], name='input')
    network = tflearn.embedding(network, input_dim=1000000, output_dim=128)
    branch1 = conv_1d(network, 128, 3, padding='valid', activation='relu', regularizer="L2")
    branch2 = conv_1d(network, 128, 4, padding='valid', activation='relu', regularizer="L2")
    branch3 = conv_1d(network, 128, 5, padding='valid', activation='relu', regularizer="L2")
    network = merge([branch1, branch2, branch3], mode='concat', axis=1)
    network = tf.expand_dims(network, 2)
    network = global_max_pool(network)
    network = dropout(network, 0.8)
    network = fully_connected(network, 2, activation='softmax')
    network = regression(network, optimizer='adam', learning_rate=0.0013,
                         loss='categorical_crossentropy', name='target')
    # Training
    model = tflearn.DNN(network, tensorboard_verbose=3)
    model.fit(trainX, trainY,
              n_epoch=5, shuffle=True, validation_set=(testX, testY),
              show_metric=True, batch_size=100,run_id="spam")
 

# def do_rnn_wordbag(trainX, testX, trainY, testY):
    # global max_document_length
    # print "RNN and wordbag"

    # trainX = pad_sequences(trainX, maxlen=max_document_length, value=0.)
    # testX = pad_sequences(testX, maxlen=max_document_length, value=0.)
    # # Converting labels to binary vectors
    # trainY = to_categorical(trainY, nb_classes=2)
    # testY = to_categorical(testY, nb_classes=2)

    # # Network building
    # net = tflearn.input_data([None, max_document_length])
    # net = tflearn.embedding(net, input_dim=10240000, output_dim=128)
    # net = tflearn.lstm(net, 128, dropout=0.8)
    # net = tflearn.fully_connected(net, 2, activation='softmax')
    # net = tflearn.regression(net, optimizer='adam', learning_rate=0.001,
                             # loss='categorical_crossentropy')

    # # Training
    # model = tflearn.DNN(net, tensorboard_verbose=0)
    # model.fit(trainX, trainY, validation_set=(testX, testY), show_metric=True,
              # batch_size=10,run_id="spm-run",n_epoch=5)


# def do_dnn_wordbag(x_train, x_test, y_train, y_testY):
    # print "DNN and wordbag"

    # # Building deep neural network
    # clf = MLPClassifier(solver='lbfgs',
                        # alpha=1e-5,
                        # hidden_layer_sizes = (5, 2),
                        # random_state = 1)
    # print  clf
    # clf.fit(x_train, y_train)
    # y_pred = clf.predict(x_test)
    # print metrics.accuracy_score(y_test, y_pred)
    # print metrics.confusion_matrix(y_test, y_pred)



def  get_features_by_tf():
    global  max_document_length
    x=[]
    y=[]
    ham, spam=load_all_files()
    x=ham+spam
    y=[0]*len(ham)+[1]*len(spam)
    vp=tflearn.data_utils.VocabularyProcessor(max_document_length=max_document_length,
                                             min_frequency=0,
                                             vocabulary=None,
                                             tokenizer_fn=None)
    x=vp.fit_transform(x, unused_y=None)
    x=np.array(list(x))
    return x,y

def get_features_by_wordbag_tfidf():
    ham, spam=load_all_files()
    x=ham+spam
    y=[0]*len(ham)+[1]*len(spam)
    vectorizer = CountVectorizer(binary=False,
                                 decode_error='ignore',
                                 strip_accents='ascii',
                                 max_features=max_features,
                                 stop_words='english',
                                 max_df=1.0,
                                 min_df=1 )
    print vectorizer
    x=vectorizer.fit_transform(x)
    x=x.toarray()
    transformer = TfidfTransformer(smooth_idf=False)
    print transformer
    tfidf = transformer.fit_transform(x)
    x = tfidf.toarray()
    return  x,y

def do_metrics(y_test,y_pred):
    print "metrics.accuracy_score:"
    print metrics.accuracy_score(y_test, y_pred)
    print "metrics.confusion_matrix:"
    print metrics.confusion_matrix(y_test, y_pred)
    print "metrics.precision_score:"
    print metrics.precision_score(y_test, y_pred)
    print "metrics.recall_score:"
    print metrics.recall_score(y_test, y_pred)
    print "metrics.f1_score:"
    print metrics.f1_score(y_test,y_pred)

if __name__ == "__main__":
    print "Hello spam-mail"
    print "get_features_by_wordbag"
    x,y=get_features_by_wordbag()
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size = 0.4, random_state = 0)

    #print "get_features_by_wordbag_tfidf"
    #x,y=get_features_by_wordbag_tfidf()
    #x_train, x_test, y_train, y_test = train_test_split(x, y, test_size = 0.4, random_state = 0)


    #print "get_features_by_tf"
    #x,y=get_features_by_2gram_tfidf()
    #x_train, x_test, y_train, y_test = train_test_split(x, y, test_size = 0.4, random_state = 0)
    # CNN
    #do_cnn_wordbag(x_train, x_test, y_train, y_test)
    do_dccnn(x_train, x_test, y_train, y_test)
    #show_diffrent_max_features()
