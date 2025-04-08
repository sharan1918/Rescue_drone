// import 'dart:convert';
// import 'package:flutter/material.dart';
// import 'package:flutter_webrtc/flutter_webrtc.dart';
// import 'package:http/http.dart' as http;

// void main() => runApp(MyApp()); // ✅ Add main() function

// class MyApp extends StatelessWidget {
//   @override
//   Widget build(BuildContext context) {
//     return MaterialApp(
//       home: WebRTCStreaming(), // ✅ Start with WebRTC Streaming
//       debugShowCheckedModeBanner: false,
//     );
//   }
// }

// class WebRTCStreaming extends StatefulWidget {
//   @override
//   _WebRTCStreamingState createState() => _WebRTCStreamingState();
// }

// class _WebRTCStreamingState extends State<WebRTCStreaming> {
//   RTCPeerConnection? _peerConnection;
//   MediaStream? _localStream;
//   final RTCVideoRenderer _localRenderer = RTCVideoRenderer();
//   String signalingServer =
//       "https://4f2a-106-51-168-0.ngrok-free.app"; // ✅ Update with your Ngrok URL

//   @override
//   void initState() {
//     super.initState();
//     _initWebRTC();
//   }

//   Future<void> _initWebRTC() async {
//     await _localRenderer.initialize();
//     await _startCamera();
//     await _connectToSignaling();
//   }

//   Future<void> _startCamera() async {
//     final Map<String, dynamic> mediaConstraints = {
//       'video': {
//         'facingMode': 'environment',
//       }, // ✅ Rear camera for better streaming
//       'audio': false,
//     };

//     _localStream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
//     setState(() {
//       _localRenderer.srcObject = _localStream;
//     });
//   }

//   Future<void> _connectToSignaling() async {
//     _peerConnection = await createPeerConnection({
//       'iceServers': [
//         {'urls': 'stun:stun.l.google.com:19302'},
//       ],
//     });

//     _localStream!.getTracks().forEach((track) {
//       _peerConnection!.addTrack(track, _localStream!);
//     });

//     _peerConnection!.onIceCandidate = (candidate) async {
//       var response = await http.post(
//         Uri.parse("$signalingServer/candidate"),
//         headers: {'Content-Type': 'application/json'},
//         body: jsonEncode({'candidate': candidate.toMap()}),
//       );
//       debugPrint("ICE Candidate sent: ${response.statusCode}");
//     };

//     RTCSessionDescription offer = await _peerConnection!.createOffer();
//     await _peerConnection!.setLocalDescription(offer);

//     var response = await http.post(
//       Uri.parse("$signalingServer/offer"),
//       headers: {'Content-Type': 'application/json'},
//       body: jsonEncode({'sdp': offer.sdp, 'type': offer.type}),
//     );

//     var answer = jsonDecode(response.body);
//     await _peerConnection!.setRemoteDescription(
//       RTCSessionDescription(answer['sdp'], answer['type']),
//     );
//   }

//   @override
//   void dispose() {
//     _peerConnection?.close();
//     _localStream?.dispose();
//     _localRenderer.dispose();
//     super.dispose();
//   }

//   @override
//   Widget build(BuildContext context) {
//     return Scaffold(
//       appBar: AppBar(title: Text("WebRTC Streaming")),
//       body: Center(
//         child:
//             _localStream != null
//                 ? RTCVideoView(_localRenderer)
//                 : CircularProgressIndicator(), // ✅ Show loading indicator if camera is not ready
//       ),
//     );
//   }
// }
import 'dart:async';
import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:geolocator/geolocator.dart';

List<CameraDescription>? cameras;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  cameras = await availableCameras();
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Auto Capture & Upload',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: CameraView(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class CameraView extends StatefulWidget {
  @override
  _CameraViewState createState() => _CameraViewState();
}

class _CameraViewState extends State<CameraView> {
  CameraController? controller;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    if (cameras != null && cameras!.isNotEmpty) {
      controller = CameraController(cameras![0], ResolutionPreset.medium);
      controller!.initialize().then((_) {
        if (!mounted) return;
        setState(() {});
        startAutoCapture();
      });
    }
  }

  void startAutoCapture() {
    timer = Timer.periodic(Duration(seconds: 1), (Timer t) async {
      if (controller != null && controller!.value.isInitialized) {
        takePictureAndUpload();
      }
    });
  }

  Future<void> takePictureAndUpload() async {
    if (!controller!.value.isInitialized) return;
    try {
      final XFile image = await controller!.takePicture();
      File file = File(image.path);
      await uploadImage(file);
      print("Picture taken and attempting upload...");
    } catch (e) {
      print("Error taking picture: $e");
    }
  }

  Future<void> uploadImage(File file) async {
    // First check if location services are enabled
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      print('Location services are disabled');
      return;
    }

    // Check and request location permissions
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        print('Location permissions are denied');
        return;
      }
    }
    
    if (permission == LocationPermission.deniedForever) {
      print('Location permissions are permanently denied');
      return;
    }

    // Get current location
    Position position = await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );

    var uri = Uri.parse("https://f4bd-106-51-168-0.ngrok-free.app/upload");
    var request = http.MultipartRequest('POST', uri);
    
    // Add image file
    request.files.add(await http.MultipartFile.fromPath('image', file.path));
    
    // Add location data
    request.fields['latitude'] = position.latitude.toString();
    request.fields['longitude'] = position.longitude.toString();

    try {
      var response = await request.send();
      if (response.statusCode == 200) {
        print("Upload successful");
      } else {
        print("Upload failed: ${response.statusCode}");
      }
    } catch (e) {
      print("Upload error: $e");
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Auto Capture & Upload"),
      ),
      body: controller == null || !controller!.value.isInitialized
          ? Center(child: CircularProgressIndicator())
          : CameraPreview(controller!),
    );
  }
}
