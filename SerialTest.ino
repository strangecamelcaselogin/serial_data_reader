int time = 0;
char buff[20];

void setup() {
  Serial.begin(9600);
}

void loop() {
  time++;
  
  int value = time * time / time;
  memset(buff, ' ', sizeof buff);  
  sprintf(buff, "%i;%i", time, value);
  Serial.println(buff);
  
  delay(10);
}
