#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_err.h"

void app_main(void) {
    ESP_ERROR_CHECK(gpio_reset_pin(GPIO_NUM_23));
    ESP_ERROR_CHECK(gpio_set_direction(GPIO_NUM_23, GPIO_MODE_OUTPUT));
    int level = 0;
    while (1) {
        level = !level;
        ESP_ERROR_CHECK(gpio_set_level(GPIO_NUM_23, level));
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
