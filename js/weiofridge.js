var freezerTemp, fridgeTemp, kitchenTemp, kitchenHumidity;
var lastUpdate=Date.now();

//=================================================================================================
// Called when page is loaded and WebSocket is ready
//=================================================================================================
function onWeioReady() {

    // Setting Python message callback funtion to process received data
    weioCallbacks["updateData"] = updateDashboard;

    // Creating gauges
    freezerTemp = new JustGage({
        id: "freezerTemp", 
        value: -20, min: -20, max: -5,
        title: "Freezer", label: "°C",
        levelColorsGradient: false,
        levelColors: [ "#CCFFFF", "#80FFFF", "#D6EBFF" ]
    });

    fridgeTemp = new JustGage({
        id: "fridgeTemp", 
        value: 0, min: 0, max: 15,
        title: "Fridge", label: "°C",
        levelColorsGradient: false,
        levelColors: [ "#80FFFF", "#3399FF", "#FF9900" ]
    });

    kitchenTemp = new JustGage({
        id: "kitchenTemp", 
        value: 0, min: 10, max: 30,
        title: "Temp", label: "°C",
        levelColorsGradient: false,
        levelColors: [ "#3399FF", "#00CC00", "#CC0000" ]
    });

    kitchenHumidity = new JustGage({
        id: "kitchenHumidity", 
        value: 0, min: 0, max: 100,
        title: "Humidity", label: "%",
        levelColors: [ "#D6EBFF", "#000099" ]
    });

    // Asking for data for the first time (not waiting next update)
    // by sending a message to Python backend
    genericMessage("requestData",0);

    // Updates displayed timer every seconds 
    setInterval(function(){
        interval=((Date.now() - lastUpdate) / 1000).toFixed(0);
        document.getElementById('timer').innerHTML = "Last update " + interval + " second(s) ago";
    },1000)    
    
}
 
//=================================================================================================
// Callback function called when "updateData" message received from Python backend
//=================================================================================================
function updateDashboard(data) {

    // Setting timer html element and reseting lastUpdate    
    document.getElementById('timer').innerHTML = "Updating...";
    lastUpdate = Date.now();

    // Parse JSON data received from Python into JS object
    var jsonData=JSON.parse(data);
    
    // Updating Gauges
    for(var key in jsonData) {
        
        switch(key) {
            case "287A4D14040000E4": freezerTemp.refresh(jsonData[key].toFixed(1)); break;
            case "28FC9AE0030000B6": fridgeTemp.refresh(jsonData[key].toFixed(1)); break;
            case "temperature"     : kitchenTemp.refresh(jsonData[key].toFixed(1)); break;
            case "humidity"        : kitchenHumidity.refresh(jsonData[key].toFixed(1)); break;
        }
    }
}
