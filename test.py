import pandas as pd
import numpy as np
from scipy import sparse
import os
import pickle
import config
import glob
import sys
import traceback

###########################################################################################################################
# # Author      : Tapas Mohanty                                                                                        
# # Functionality : Importing the pickle files for model, vector from the model folder
# ###########################################################################################################################

class MyCustomUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "__main__":
            module = "custom_token"
        return super().find_class(module, name)
        
def loadTfidfFile(pRootDir, pModelName):
    vec_loc = pRootDir + '\\' + str(pModelName)  + '\\' + str(pModelName[6:]) + '_Vector'  +'\\' + str(pModelName[6:])  +  ".vector.pkl"
    with open(vec_loc, 'rb') as f:
        unpickler = MyCustomUnpickler(f)
        vec = unpickler.load()
    return vec

def loadcsr_matrix(pRootDir, pModelName, pIntent):
    r_loc = pRootDir + '\\' +  str(pModelName) + '\\' + str(pModelName[6:]) +  '_Csr_matrix' + '\\' +  str(pIntent) + ".npz"
    r = sparse.load_npz(r_loc)
    return r
    
def loadmodel(pRootDir, pModelName, pIntent):
    model_loc = pRootDir + '\\' +  str(pModelName) + '\\' + str(pModelName[6:]) +  '_Model' + '\\' + str(pIntent) + ".model.pkl"
    with open(model_loc, 'rb') as f:
        unpickler = MyCustomUnpickler(f)
        model = unpickler.load()
    return model

def categories(pRootDir, pModelName):
    path = pRootDir + '\\' +  str(pModelName) + '\\' + str(pModelName[6:]) +  '_Model' + '\\'
    file = glob.glob(path +'/*.model.pkl')
    category_names =  []
    for i in range(len(file)):
        basename = os.path.basename(file[i])
        category_names.append(basename.split('.model.pkl')[0])
    return category_names


# ###########################################################################################################################
# # Author      : Tapas Mohanty                                                                                        
# # Functionality : Find intent for the tickets which has low thershold value by using NB-SVM and Logistic Regression
# ###########################################################################################################################
def intentpred(pData, pDesc, pTh, pTicketId, pModelName, pRootDir):

    try:
        pData[pDesc].fillna("unknown", inplace=True)  
        category_names = categories(pRootDir, pModelName)
        pData[pTicketId] = pData[pTicketId].astype('category') 
        preds = np.zeros((len(pData), len(category_names)))
        
        vec = loadTfidfFile(pRootDir, pModelName)
        tkt_desc = vec.transform(pData[pDesc].astype(str))
        
        for index,name in enumerate(category_names):
            print('Calculating prediction of intent', name)
            estimator = loadmodel(pRootDir, pModelName, name)           
            r = loadcsr_matrix(pRootDir, pModelName, name)
            preds[:,index] = estimator.predict_proba(tkt_desc.multiply(r))[:,1]      
        pintentdf = pd.DataFrame(preds, columns = category_names)
        pintentdf['Confidence_Level'] = pintentdf[category_names].max(axis=1)
        pintentdf['Intent'] = pintentdf[category_names].idxmax(axis=1)
        pintentdf['Intent']= np.where(pintentdf['Confidence_Level'] > float(pTh), pintentdf['Intent'] , 'Others') 
        pData.reset_index(drop=True, inplace=True)
        pintentdf.reset_index(drop=True, inplace=True)
        pintentdf = pd.concat([pData[config.pTicketId], pintentdf],axis=1)   
        pintentdf = pintentdf[[config.pTicketId, 'Confidence_Level', 'Intent']]
        pData.loc[pData[config.pTicketId].isin(pintentdf[config.pTicketId]), ['Confidence_Level', 'Intent']] = pintentdf[['Confidence_Level', 'Intent']].values
        pData[[config.pLevel1,config.pLevel2]] = pData.Intent.str.split("__",expand=True,)
 
    except Exception as e:
        print(e)
        print('*** ERROR[001]: intentpred ***', sys.exc_info()[0],str(e))
        print(traceback.format_exc())
        return(-1, pData) 
    return(0, pData)
