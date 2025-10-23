# -- coding: utf-8 --
"""
Visualizador de dados do experimento do LDR - Python + Arduino
Vitor R. Coluci	
baseado no códido de 
Victor Richard Cardoso/USP/Oficiencia
e https://www.youtube.com/watch?v=0V-6pu1Gyp8

https://www.youtube.com/watch?v=zH0MGNJbenc

MODULOS

1) CALIBRAR: opcao usada para fazer a calibracao usando o laser vermelho (650nm)
Nesse modo, a coleta eh feita da direita para a esquerda. Terminada a coleta, o LDR retorna para sua possicao inicial (extrema direita). Os 3 minimos esperados para R sao determinados.
O grafico apresentado eh R vs Passos com os 3 minimos indicados com circulos.

2) SINGLE (MEDIDA UNICA): com a calibracao realizada, essa opcao coleta uma unica medida para verificar se os dados estao OK para realizar o batch (varias medidas).
Para essa opcao, o Laser deve estar desligado e a luz branca ligada.
O grafico gerado pode ser R vs passo ou R vs Energia, que pode ser escolhido com o 
botao On/OFF no canto inferior direito do app.
A coleta eh feita da direita para a esquerda e o LDR retorna a sua posicao original ao final.

3) FUNDO BATCH: essa opcao eh para coleta a luz de fundo, estando o Laser e a luz branca desligadas.
Varias medidas sao feitas (batch) e o grafico da media dessas medidas com o respectivo desvio padrao (barras de erro) e mostrado.
O grafico eh R vs passo.

4) BATCH:  Essa opcao eh para obter o grafico principal R vs Energia. Ela faz varias medidas (mesmo numero do Fundo Batch)
calcula a media e desvio padrao e mostra o grafico com barras de erros.

Para as opcoes 3) e 4), os dados sao verificados para eliminar dados com problemas (Inf ou Nan), usando apenas os dados validos para calcular media e e fazer grafico.

Observacoes:
a) O numero de medidas para as opcoes 3) e 4) deve ser IGUAL ao numero informado no programa usado no Arduino.

b) Uma vez feita a calibracao, tendo determinado o fator de conversao, esse fator pode ser informado na linha 100. Com isso, caso precise reiniciar o programa, nao sera mais necessario realizar a calibracao. Pode-se seguir com  a medida unica e batch.

"""

# bibliotecas
from tkinter import *
from tkinter import ttk
from tkinter import font
from PIL import Image
from PIL import ImageTk
import serial
import numpy as np
import time
import matplotlib.pyplot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
from matplotlib.figure import Figure
import math

###########################################################
# parametros

# localização da porta serial
porta_serial='/dev/ttyACM0'

# comprimento de onda (em nm) do laser usado na calibração
comp_onda = 653.0

#maximo valor de resistencia para gráfico (Ohms)
max_valor_resistencia = 10000000

grafico_energia = 1 # 1 se quiser imprimir energia no eixo x; 0 se quiser passo no eixo x

# numero total de pontos de leitura 
n = 5000

# numero total de medidas independentes (batch)
n_batch = 10   # esse valor precisa ser igual ao que esta no programa do Arduino

# imprime na serial a cada passo passos
passo = 10

# numero de linhas da matriz media
n_print = int(n/passo)

# resolução da tela (laptop/PC)
#l=1200
#h=800
l=1800
h=900

# largura e altura dos botões
l_b= l/8
h_b= h/8

# imagem Logo 156x43
l_logo=156
h_logo=43

x = []
y = []

# inicializa id_medida para impressao de arquivos de medidas single/calibração
id_medida = 0
id_medida_calib = 0

fator_conversao = 0.368926

is_on = True

minimos = []

###########################################################

# funções

###########################################################		
# criação das estruturas gráficas (eixos, grids, cores, labels, etc)
def prepara_grafico():
    global grafico,plt1,canvas,n,max_valor_resistencia,grafico_energia
    
    grafico = Figure(figsize=(3*l/380,h/120)) # size em polegadas
    grafico.subplots_adjust(hspace=0.2)
    grafico.set_facecolor('black')
    grafico.tight_layout()

    # grafico 
    plt1 = grafico.add_subplot(111)
    plt1.grid(linewidth=1)
    plt1.set_facecolor('black')
    plt1.spines['bottom'].set_color('orange')
    plt1.spines['bottom'].set_linewidth(3)
    plt1.spines['top'].set_color('orange')
    plt1.spines['top'].set_linewidth(3)
    plt1.spines['left'].set_color('orange')
    plt1.spines['left'].set_linewidth(3)
    plt1.spines['right'].set_color('orange')
    plt1.spines['right'].set_linewidth(3)
    
    # Títulos dos eixos
    if (grafico_energia==0):
        plt1.set_xlabel('Passo',color='white',fontsize=fonte1['size'])
    else:
        plt1.set_xlabel('Energia (eV)',color='white',fontsize=fonte1['size'])

    plt1.set_ylabel('Resistência [Ohms]',rotation='vertical',color='white',fontsize=fonte1['size'])
    plt1.tick_params('both',labelcolor='white',labelsize=fonte1['size'])
    
    # range em x
    if (grafico_energia==0):
        plt1.set_xlim(xmin=0,xmax=5000)
    else:
        plt1.set_xlim(xmin=1.3,xmax=3.0)
    
    # range em y
    plt1.set_ylim(ymin=0,ymax=max_valor_resistencia)
       
    canvas = FigureCanvasTkAgg(grafico, master=frame_1)
    canvas.get_tk_widget().grid(row=0,column=0, sticky='EWNS')

###########################################################   
# calibracao com laser para obter fator de conversao de passo para comprimento de onda
def calibracao():
    global x,y,n,passo,comp_onda,grafico_energia,fator_conversao,minimos
    
    x = []
    y = []
    print("=========== Calibração ===========\n")
    # 1) coleta os dados
    k = 0
    idx=[]
    kk=-1
    while( k < n ):		
      dados = s.readline().decode().split(',')   #lê a linha de texto da serial
      k += 1 #aqui incrementa k para indicar que foi realizada uma medida
	    
      if (k % passo == 0):
        x.append(float( dados[0] ))               
        y.append(float( dados[1] ))
        kk += 1
        print(dados)
        idx.append(kk)
        
    # 2) Acha os mínimos de resistência (máximos de luz no LDR)
    xx=np.arange(len(x))
    yy=np.arange(len(y))
    xx = np.array(x)
    yy = np.array(y)
    # acha minimo 1
    minimo1 = np.min(yy)
    for j in range(n_print):
        if (yy[j] == minimo1):
            pos_minimo1 = j

    # acha minimo 2
    # isola local onde está o minimo1 para não encontra-lo novamente
    lmax1 =  xx[pos_minimo1] + 1000
    lmin1 =  xx[pos_minimo1] - 1000
    minimo2 = 10000000000
    for j in range(n_print):
        if (xx[j] < lmin1 or xx[j] > lmax1):
            if (yy[j] < minimo2):
                minimo2 = yy[j]
                pos_minimo2 = j

    # acha minimo 3
    # isola local onde está o minimo2 para não encontra-lo novamente
    lmax2 =  xx[pos_minimo2] + 1000
    lmin2 =  xx[pos_minimo2] - 1000
    minimo3 = 10000000000
    
    #print(lmin1,lmax1,lmin2,lmax2)
    for j in range(n_print):
        if (xx[j] < lmin1 or xx[j] > lmax1 ):
            if (xx[j] < lmin2 or xx[j] > lmax2 ):
                if (yy[j] < minimo3):
                    minimo3 = yy[j]
                    pos_minimo3 = j
    
    posicao_minimos = []
    posicao_minimos.append(pos_minimo1)
    posicao_minimos.append(pos_minimo2)
    posicao_minimos.append(pos_minimo3)
    posicoes_ordenadas = sorted(posicao_minimos)
       
    print(" >> Mínimos <<")
    print(xx[pos_minimo1],yy[pos_minimo1])
    print(xx[pos_minimo2],yy[pos_minimo2])
    print(xx[pos_minimo3],yy[pos_minimo3])
    
    
    minimos.append(int(idx[pos_minimo1]))
    minimos.append(int(idx[pos_minimo2]))
    minimos.append(int(idx[pos_minimo3]))
    
    print(" >> Simetria << os 2 numeros a seguir devem ser iguais\n")
    print(xx[posicoes_ordenadas[1]] - xx[posicoes_ordenadas[0]])
    print(xx[posicoes_ordenadas[2]] - xx[posicoes_ordenadas[1]])
    
    # 3) calcula fator de conversão
    
    deltax = xx[posicoes_ordenadas[2]] - xx[posicoes_ordenadas[1]]
    fator_conversao = comp_onda/deltax
    
    print(" >> Fator de conversão [nm/passos] <<")
    print(fator_conversao)
    print(minimos)

    #max_valor_resistencia = np.max(yy) + 1000
    
    # limpa arrays
    np.delete(xx,range(len(xx)))
    np.delete(yy,range(len(yy)))

###########################################################
# Coleta dados lidos da serial (medida única)
def single():
    global s,x,y,n,passo,fator_conversao,grafico_energia	
    k = 0
    i = 0
    
    # np arrays para guardar dados    
    data_x = np.zeros(n_print)
    data_y = np.zeros(n_print)
    
    while( k < n ):		
      dados = s.readline().decode().split(',')   #lê a linha de texto da serial
      k += 1 #aqui incrementa k para indicar que foi realizada uma medida
      if (k % passo == 0):
        data_x[i] =  float( dados[0] )             
        data_y[i] =  float( dados[1] )
        i += 1

    if (grafico_energia==1):
        # acha minimo supondo que ele esteja proximo ao centro
        minimo = 10000000000
        for j in range(n_print):
            if (j > n_print/2 -10 and j < n_print/2 + 10):
               if (data_y[j] < minimo):
                 pos_minimo = j
                 minimo = data_y[j]
                 
        xminimo = data_x[pos_minimo]
        print(pos_minimo,xminimo) 
        # coloca pico central em passo=0 e converte para nm (fator_conversao vem da calibração)
        for j in range(n_print):
            #data_x[j] = (data_x[j] - xminimo)*fator_conversao
            data_x[j] = -1.0*(data_x[j] - xminimo)*fator_conversao # -1 eh para usar lado que tem mais intensidade
            
        # conversao de nm para eV
        for j in range(n_print):
            if (data_x[j] == 0):
                data_x[j] = 1242.0/0.001
            else:
                data_x[j] = 1242.0/data_x[j]
        
    # coloca dados em listas para plotar
    x=[]
    y=[]
    x=data_x.tolist()
    y=data_y.tolist()  
  
    
    # limpa arrays
    np.delete(data_x,range(len(x)))
    np.delete(data_y,range(len(y)))

###########################################################
# Coleta dados batch para medida sem luz (fundo)  R vs passos
def fundo():
    global max_valor_resistencia,s,x,y,data_passo_validas,data_passo,data_media,data_sd,n,passo,n_print,n_batch,fator_conversao
    x = []
    y = []
    
    # use mais pontos para o caso do grafico de energia
    passo_batch = passo #/5
    n_print_batch = n_print#*5

    data_passo = np.zeros(n_print_batch)
    data_media = np.zeros(n_print_batch)
    data_sd    = np.zeros(n_print_batch)
    data_medidas = np.zeros((n_print_batch,n_batch))
    
    print(" >> Fundo Batch <<")
    k = 0
    i = 0
    medida = 0
    
    while( k < n * n_batch ):
      dados = s.readline().decode().split(',')   #lê a linha de texto da serial
      k += 1 #aqui incrementa k para indicar que foi realizada uma medida
      #print(k)	
      if (k % passo_batch == 0):
        #print(passo_batch,k)
        data_passo[i] =  float( dados[0] )             
        data_medidas[i][medida] = float( dados[1] )
        x.append(float( dados[0] ))               
        y.append(float( dados[1] ))
        i += 1
        
        if (i > n_print_batch - 1):
          i = 0
          arr = np.stack((x, y), axis=1)
          np.savetxt("medida-fundo-"+str(medida+1)+".dat",arr,fmt = ["%1.5f", "%1.5f"],delimiter = ' ')
          x = []
          y = []
          medida += 1
          print(" Medida Fundo Batch = "+str(medida)+" de "+str(n_batch)+" Pronta!")
    
    # verifica a presenca de inf e nan
    n_validas = 0
    for i in range(n_print_batch):
        teste = 0
        for j in range(n_batch):
            ss = data_medidas[i][j]
            if ( np.isnan(ss) or np.isinf(ss) ):
              teste = 1
        
        if (teste == 0):
          n_validas += 1

    data_passo_validas = np.zeros(n_validas)
    data_media = np.zeros(n_validas)
    data_sd    = np.zeros(n_validas)
    data_medidas_validas = np.zeros((n_validas,n_batch))

    # coleta medidas validas
    k = 0
    for i in range(n_print_batch):
        teste = 0
        for j in range(n_batch):
            ss = data_medidas[i][j]
            if ( np.isnan(ss) or np.isinf(ss) ):
              teste = 1
        
        if (teste == 0):
          data_passo_validas[k] = data_passo[i]
          for j in range(n_batch):
            data_medidas_validas[k][j] = data_medidas[i][j]
          k += 1 

    # calcula media e desvio padrao
    print("Calculando media e desvio padrao")

    for i in range(n_validas):
        # media
        soma = 0.0
        for j in range(n_batch):
            soma += data_medidas_validas[i][j]
        
        media = soma/n_batch
        data_media[i] = media
        
        # desvio padrao
        sd = 0.0
        for j in range(n_batch):
            sd += (data_medidas_validas[i][j] - media)*(data_medidas_validas[i][j] - media)
        
        data_sd[i] = np.sqrt( sd / (n_batch-1) )

    # calcula media global e desvio padrao global
    # ja que se espera que o resultado seja uma linha reta horizontal
    
    # media geral
    soma = 0.0
    num = 0
    for i in range(n_validas):
        for j in range(n_batch):
            soma += data_medidas_validas[i][j]
            num += 1
    
    media = soma/num
    
    # desvio padrao geral
    sd = 0.0
    for i in range(n_validas):
        for j in range(n_batch):
            sd += (data_medidas_validas[i][j] - media)*(data_medidas_validas[i][j] - media)

    sd = np.sqrt( sd / (num-1) )

    print("Media e desvio padrao -->> calculados !")
    print("Media e desvio padrao GERAL -->> ")
    print(media,sd)
    
    max_valor_resistencia = 2.0*media
    
###########################################################        
def batch():
    global max_valor_resistencia,s,x,y,data_passo_validas,data_passo,data_media,data_sd,n,passo,n_print,n_batch,fator_conversao,grafico_energia
    x = []
    y = []
     
    passo_batch = passo #/5
    n_print_batch = n_print # *5

    data_passo = np.zeros(n_print_batch)
    data_media = np.zeros(n_print_batch)
    data_sd    = np.zeros(n_print_batch)
    data_medidas = np.zeros((n_print_batch,n_batch+1))
    
    print(" >> Batch <<")
    k = 0
    i = 0
    medida = 0
    
    while( k < n * n_batch ):
      dados = s.readline().decode().split(',')   #lê a linha de texto da serial
      k += 1 #aqui incrementa k para indicar que foi realizada uma medida
      
      if (k % passo_batch == 0):
        data_passo[i] =  float( dados[0] )             
        data_medidas[i][medida] = float( dados[1] )
        x.append(float( dados[0] ))               
        y.append(float( dados[1] ))
        i += 1
        
        if (i > n_print_batch - 1):
          i = 0
          arr = np.stack((x, y), axis=1)
          np.savetxt("medida-"+str(medida+1)+".dat",arr,fmt = ["%1.5f", "%1.5f"],delimiter = ' ')
          x = []
          y = []
          medida += 1
          print(" Medida Batch = "+str(medida)+" de "+str(n_batch)+" Pronta!")
    
    # verifica a presenca de inf e nan
    n_validas = 0
    for i in range(n_print_batch):
        teste = 0
        for j in range(n_batch):
            ss = data_medidas[i][j]
            if ( np.isnan(ss) or np.isinf(ss) ):
              teste = 1
        
        if (teste == 0):
          n_validas += 1

    data_passo_validas = np.zeros(n_validas)
    data_media = np.zeros(n_validas)
    data_sd    = np.zeros(n_validas)
    data_medidas_validas = np.zeros((n_validas,n_batch))

    print("Porcentagem medidas validas = ",100.0*n_validas/n_print_batch," %")
      
    # coleta medidas validas
    k = 0
    for i in range(n_print_batch):
        teste = 0
        for j in range(n_batch):
            ss = data_medidas[i][j]
            #se tiver alguma medida com problema, desconsidere-a
            if ( np.isnan(ss) or np.isinf(ss) ):
              teste = 1
        # guarde apenas as medidas sem problema
        if (teste == 0):
          data_passo_validas[k] = data_passo[i]
          for j in range(n_batch):
            data_medidas_validas[k][j] = data_medidas[i][j]
          k += 1 

    # calcula media e desvio padrao
    print("Calculando media e desvio padrao")

    for i in range(n_validas):
        # media
        soma = 0.0
        for j in range(n_batch):
            soma += data_medidas_validas[i][j]
        
        media = soma/n_batch
        data_media[i] = media
        
        # desvio padrao
        sd = 0.0
        for j in range(n_batch):
            sd += (data_medidas_validas[i][j] - media)*(data_medidas_validas[i][j] - media)
        
        data_sd[i] = np.sqrt( sd / (n_batch-1) )

    print("Media e desvio padrao -->> calculados !")
    
    #max_valor_resistencia = np.max(data_media) + 1000  
    
    if (grafico_energia==1):
        print("preparacao de dados para grafico de Energia")
        data_x = np.zeros(n_validas)   
        data_x = data_passo_validas  
        data_passo = np.zeros(n_validas) 
        
        minimo = np.min(data_media)
        
        for j in range(n_validas):
            if (data_media[j] == minimo):
                pos_minimo = j
        
        xminimo = data_x[pos_minimo]         
        
        # coloca pico central em passo=0 e converte para nm 
        #(fator_conversao vem da calibração)
        for j in range(n_validas):
            data_x[j] = -1.0*(data_x[j] - xminimo)*fator_conversao

        # conversao de nm para eV
        for j in range(n_validas):
            if (data_x[j] == 0):
                data_passo[j] = 1242.0/0.001
            else:
                data_passo[j] = 1242.0/data_x[j]
        
        np.delete(data_x,range(n_validas))
        
        # remove valores de energia fora da regiao de interesse (negativos e maiores que 5 eV)
        
        n_interesse = 0
        for i in range(n_validas):
        	if (data_passo[i] > 0.0 and data_passo[i] < 5.0):
        		n_interesse += 1
               
        data_passo_interesse = np.zeros(n_interesse)
        data_media_interesse = np.zeros(n_interesse)
        data_sd_interesse = np.zeros(n_interesse)
        
        k=0
        for i in range(n_validas):
            if (data_passo[i] > 0.0 and data_passo[i] < 5.0):
               data_passo_interesse[k] = data_passo[i]
               data_media_interesse[k] = data_media[i]
               data_sd_interesse[k] = data_sd[i]
               k += 1
               
        np.delete(data_passo,range(n_validas))
        np.delete(data_media,range(n_validas))
        np.delete(data_sd,range(n_validas)) 
        
        data_passo = np.zeros(n_interesse)
        data_media = np.zeros(n_interesse)
        data_sd = np.zeros(n_interesse)
        
        for i in range(n_interesse):
               data_passo[i] = data_passo_interesse[i]
               data_media[i] = data_media_interesse[i]
               data_sd[i] = data_sd_interesse[i]            
        
        print("dados preparados !")
    
###########################################################    
# Coleta os dados da serial e faz o gráfico
def coleta_single():
    global s,id_medida,x,y,max_valor_resistencia
    s.write(str.encode("A"))
    
    single()
    
    # salva dados em arquivo
    print(" Salvando single em arquivo ...!")
    id_medida += 1
    arr = np.stack((x, y), axis=1)
    np.savetxt("medida-unica-"+str(id_medida)+".dat",arr,fmt = ["%1.5f", "%1.5f"],delimiter = ' ') 
    print(" Arquivo medida-single salvo !")
    
    # faz grafico
    print(" Preparando grafico ....")
    prepara_grafico()
    print(" Grafico preparado !")
    print(" Fazendo o grafico ....")
    plt1.plot(x,y,linestyle='-',color="white",alpha=0.7,markersize=10)
    canvas.draw()    
    print(" Grafico pronto !")
    
    # traz de volta o LDR
    s.write(str.encode("B"))

###########################################################    
# Coleta fundo e faz o gráfico
def coleta_fundo():
    global max_valor_resistencia,s,data_passo,data_passo_validas,data_media,data_sd,grafico_energia
    s.write(str.encode("C"))
    
    fundo()
    
    print(" Salvando batch fundo media em arquivo ...!")
    arr = np.stack((data_passo_validas,data_media,data_sd), axis=1)
    np.savetxt("media-fundo.dat",arr,fmt = ["%1.5f", "%1.5f", "%1.5f"],delimiter = ' ')
    print(" Arquivo media-fundo.dat salvo !")
    
    print(" Preparando grafico ....")
    old = grafico_energia
    grafico_energia=0
    prepara_grafico()
    print(" Grafico preparado !")
    
    print(" Fazendo o grafico ....")
    plt1.errorbar(data_passo_validas,data_media,yerr=data_sd,linestyle='-',marker='o',color="white",alpha=0.7,markersize=10)
    canvas.draw()
    print(" Grafico pronto !")
    grafico_energia = old

###########################################################
def coleta_batch():
    global max_valor_resistencia,s,data_passo,data_media,data_sd
    s.write(str.encode("C"))
    
    batch()
    
    print(" Salvando batch em arquivo ...!")
    print(len(data_passo),len(data_media),len(data_sd))
    arr = np.stack((data_passo,data_media,data_sd), axis=1)
    np.savetxt("media-batch.dat",arr,fmt = ["%1.5f", "%1.5f", "%1.5f"],delimiter = ' ')
    print(" Arquivo media-batch.dat salvo !")
    
    print(" Preparando grafico ....")
    prepara_grafico()
    print(" Grafico preparado !")
    
    print(" Fazendo o grafico ....")
    plt1.errorbar(data_passo,data_media,yerr=data_sd,linestyle='-',marker='o',color="white",alpha=0.7,markersize=10)
    canvas.draw()
    print(" Grafico pronto !")

###########################################################
def coleta_calibracao():    
    global max_valor_resistencia,s,id_medida_calib,x,y,grafico_energia,minimos
    s.write(str.encode("A"))
    
    calibracao()
    
    # salva dados em arquivo
    print(" Salvando calibração em arquivo ...!")
    id_medida_calib += 1
    arr = np.stack((x, y), axis=1)
    np.savetxt("medida-calibracao-"+str(id_medida_calib)+".dat",arr,fmt = ["%1.5f", "%1.5f"],delimiter = ' ') 
    print(" Arquivo medida-calibracao salvo!")
    
    print(" Preparando grafico ....")
    old = grafico_energia
    grafico_energia=0
    prepara_grafico()
    print(" Grafico preparado !")
    
    print(" Fazendo o grafico ....")
    plt1.plot(x,y,markevery=minimos,linestyle='-',marker='o',color="white",alpha=0.7,markersize=10)
    canvas.draw()
    grafico_energia = old
    print(" Grafico pronto !")

    print(" Calibracao pronta !")
    
    # traz de volta o LDR
    s.write(str.encode("B"))
    

###########################################################   
def sai():
    try: 
        s.close()
        janela.destroy()
    except:
        janela.destroy()    
###########################################################

# Define tipo de grafico (energia ou passo no eixo x)
def tipo_grafico():
    global is_on,grafico_energia
     
    # Determine is on or off
    if is_on:
        button7.config(image = off)
        is_on = False
        grafico_energia = 0
    else:
        button7.config(image = on)
        is_on = True
        grafico_energia = 1
    print(' Grafico_energia = ',grafico_energia)
    prepara_grafico()
        
########################################################### 
#janela principal
janela = Tk()
janela.configure(bg='black')
janela.title('Band gap')
janela.geometry("{}x{}".format(l,h))

# image para definição de tamanho dos botões em pixels
pixelVirtual = PhotoImage(width=1, height=1)

on = PhotoImage(file = "on.png")
off = PhotoImage(file = "off.png")

#fontes
fonte1 = font.Font(janela, family='Arial', size=20, weight='bold')
fonte2 = font.Font(janela, family='Arial', size=30, weight='bold')

#frames

#para gráficos
frame_1 = Frame(janela,bg='black',height=h, width=3*l/4)
frame_1.place(x=0, y=0)

# para botões
frame_0 = Frame(janela,bg='black',height=h, width=l/4)
frame_0.place(x=3*l/4, y=0)

# botões
button1 = Button(frame_0,text="Single", font=fonte2,background='blue',fg='black',command=coleta_single,
          image=pixelVirtual,width=l_b,height=h_b,compound="c")
button1.place(x=l/8-l_b/2, y=h/2-2*h_b)
          
button3 = Button(frame_0,text="SAIR", font=fonte2,bg='blue',fg='black',command=sai,
          image=pixelVirtual,width=l_b/2,height=h_b/2,compound="c")
button3.place(x=l/8-l_b/4, y=h-7*h_b/4)    
    
button4 = Button(frame_0,text='Batch', font=fonte2,bg='blue',fg='black',command=coleta_batch,
          image=pixelVirtual,width=l_b,height=h_b,compound="c")
button4.place(x=l/8-l_b/2, y=h/2+h_b)

button5 = Button(frame_0,text="Calibrar", font=fonte2,bg='blue',fg='black',command=coleta_calibracao,
          image=pixelVirtual,width=l_b,height=h_b,compound="c")
button5.place(x=l/8-l_b/2, y=h/2-3.8*h_b)

button6 = Button(frame_0,text="Fundo batch", font=fonte2,bg='blue',fg='black',command=coleta_fundo,
          image=pixelVirtual,width=l_b,height=h_b,compound="c")
button6.place(x=l/8-l_b/2, y=h/2-h_b/2)

button7 = Button(frame_0, image = on, bd = 0,command = tipo_grafico)
button7.place(x=l/8-l_b/4, y=h-4*h_b/4)

# Logo Explora
file_in = './LogoExplora.png'
pil_image = Image.open(file_in)

pil_image = pil_image.resize((l_logo,h_logo))
photo = ImageTk.PhotoImage(pil_image)

label_logo =  Label(janela,image=photo,font=fonte1,bg='black',fg='orange')
label_logo.place(x=7.1*l/8-l_logo/2,y=h-1.2*h_logo)

###########################################################
# Início

# conecta com a serial      
s = serial.Serial(porta_serial, 9600) 

# limpa dados do buffer
s.reset_input_buffer()  

old = grafico_energia
grafico_energia=0
# apresenta grafico R vs passos
prepara_grafico()
grafico_energia = old

# main loop
janela.mainloop()
# Fim
