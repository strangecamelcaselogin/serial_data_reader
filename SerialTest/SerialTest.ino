int custom_time = 0;
char buff[20];

void setup() {
  Serial.begin(9600);
}

void loop() {
  custom_time++;
  
  int target = 30;
  String value = String(abs(sin(custom_time / 10.0)) * 20);
  String another_value = String(abs(sin(custom_time / 10.0 + 1.5)) * 20);
  sprintf(buff, "%i;%i;%s;%s", custom_time, target, value.c_str(), another_value.c_str());
  Serial.println(buff);
  
  delay(100);
}
