// Programa : Controle de motor de passo com Easydriver
// Autor : Arduino e Cia

// Pinos conectados ao Step e Dir do Easydriver
const float Rf = 10000.0; // Resistor ligado ao LDR
const float V = 5.0;     // Tensão do arduino
const int n = 15;
const int num_medidas = 10;
int pino_passo = 5;
int pino_direcao = 4;
int direcao = 3;
char d = 0;
int p,i,q;
float total,vldr,rldr;
int data[n];
int sensorPin = A1;
float average = 0;

// Quantidade de passos para uma volta completa
// Ajuste de acordo com o seu motor
int passos_motor = 5000;

void setup() 
{
  Serial.begin(9600);
  // Define os pinos como saida
  pinMode(pino_passo, OUTPUT);
  pinMode(pino_direcao, OUTPUT);
}

void loop()
{
  d= Serial.read(); 
  // Define a direcao de rotacao
  if (d=='A')   direcao = 1;
  if (d=='B')   direcao = 0;
  if (d=='C')   direcao = 2;

  // coleta
  if (direcao==1) 
  {
    digitalWrite(pino_direcao, direcao);
  
    for (int p=0 ; p < passos_motor; p++)
     {
      total=0.0;
      for (int i=0 ; i < n; i++)
       {
       data[i] = analogRead(sensorPin); 
       
       total += data[i];           
       delay(1);
       }
       
        
        average = total / n;  

        // tensão no LDR em Volts
        vldr = average*V/1023.0; // transforma valores entre 0 e 1023 para valores entre 0 e 5V
         
        // resistencia do LDR em ohms obtida a partir da lei de Ohm do circuito mostrado no início do programa
        rldr = vldr*Rf/(V-vldr); 
        
        Serial.print(p); 
        Serial.print(",");
        Serial.println(rldr);
   
        digitalWrite(pino_passo, 1);
        delay(1);
        digitalWrite(pino_passo, 0);
        delay(1);
     }
     direcao = 3;
  } 
  // volta
  if (direcao==0)
  {
    digitalWrite(pino_direcao, direcao);
    for (int p=0 ; p < passos_motor; p++)
      {
         digitalWrite(pino_passo, 1);
         delay(1);
         digitalWrite(pino_passo, 0);
         delay(1);
      }  
    direcao = 3;
  }
  // batch
  if (direcao==2) 
  {
    for (int q=0 ; q < num_medidas; q++) {
      
      direcao = 1;
      digitalWrite(pino_direcao, direcao);
      // coleta
      for (int p=0 ; p < passos_motor; p++)
      {
        total=0.0;
        for (int i=0 ; i < n; i++)
        {
        data[i] = analogRead(sensorPin); 
        total += data[i];           
        delay(1);
        }
       
        average = total / n;  

        // tensão no LDR em Volts
        vldr = average*V/1023.0; // transforma valores entre 0 e 1023 para valores entre 0 e 5V
         
        // resistencia do LDR em ohms obtida a partir da lei de Ohm do circuito mostrado no início do programa
        rldr = vldr*Rf/(V-vldr); 
        
        Serial.print(p); 
        Serial.print(",");
        Serial.println(rldr);
   
        digitalWrite(pino_passo, 1);
        delay(1);
        digitalWrite(pino_passo, 0);
        delay(1);
      }
      // aguarda
      delay(500);
      // volta
      direcao = 0;
      digitalWrite(pino_direcao, direcao);
      for (int p=0 ; p < passos_motor; p++)
      {
         digitalWrite(pino_passo, 1);
         delay(1);
         digitalWrite(pino_passo, 0);
         delay(1);
      }
      delay(500); 
    }
    direcao = 3;   
  }
}
