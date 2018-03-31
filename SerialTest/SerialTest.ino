int custom_time = 0;
char buff[20];

void setup() {
  Serial.begin(9600);
}

void loop() {
  custom_time++;
  
  int value = custom_time * custom_time / custom_time; 
  sprintf(buff, "%i;%i", custom_time, value);
  Serial.println(buff);
  
  delay(10);
}
