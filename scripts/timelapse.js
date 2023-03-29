const date = new Date();
console.log(date); // Fri Jun 17 2022 11:27:28 GMT+0100 (British Summer Time)
let day = date.getDate();
let month = date.getMonth() + 1;
let year = date.getFullYear();

// document.getElementById("day").innerHTML=day;
// document.getElementById("month").innerHTML=month;
// document.getElementById("year").innerHTML=year;






//const {Storage} = require('@google-cloud/storage');

// import * as storageModule from "@google-cloud/storage";
// const { Storage } = storageModule;

// // Creates a client
// const storage = new Storage();

// async function streamFileDownload() {
//   // The example below demonstrates how we can reference a remote file, then
//   // pipe its contents to a local file.
//   // Once the stream is created, the data can be piped anywhere (process, sdout, etc)
//   await storage
//     .bucket("date-night-qa.appspot.com/parking_lot_timelapse/videos/")
//     .file("20230326_155701.MP4")
//     .createReadStream() //stream is created
//     .pipe(fs.createWriteStream(destFileName))
//     .on('finish', () => {
//       document.getElementById("videoName1").innerHTML=videoSrcUrl;
//     });

//   console.log(
//     `gs://${bucketName}/${fileName} downloaded to ${destFileName}.`
//   );
// }

// streamFileDownload().catch(console.error);









// async function readFiles () {
//   const [files] = await bucket.getFiles({ prefix: 'date-night-qa.appspot.com/parking_lot_timelapse/videos/'});
//   console.log('Files:');
//   files.forEach(file => {
//     console.log(file);
//     document.getElementById("videoName2").innerHTML="file2 ran";
//   });
// };

// /*
// admin.storage().bucket()
// .getFiles({ prefix: 'date-night-qa.appspot.com/parking_lot_timelapse/videos/', autoPaginate: false })
// .then((files) => {
// document.getElementById("videoName2").innerHTML=videoSrcUrl;
// });

// let videoSrcUrl = "URL HERE"
// document.getElementById("videoUrl").src=videoSrcUrl;
// */

