from pyannote.database import registry
from pyannote.database.protocol import CollectionProtocol
from pyannote.database.protocol import Protocol
from pyannote.database.protocol import SpeakerDiarizationProtocol
from pyannote.database.protocol import SpeakerVerificationProtocol

assert "MyDatabase" in registry.get_databases()

database = registry.get_database("MyDatabase")
tasks = database.get_tasks()
assert "Collection" in tasks
assert "Protocol" in tasks
assert "SpeakerDiarization" in tasks
assert "SpeakerVerification" in tasks

assert "MyCollection" in database.get_protocols("Collection")
assert "MyProtocol" in database.get_protocols("Protocol")
assert "MySpeakerDiarization" in database.get_protocols("SpeakerDiarization")
assert "MySpeakerVerification" in database.get_protocols("SpeakerVerification")


collection = registry.get_protocol("MyDatabase.Collection.MyCollection")
assert isinstance(collection, CollectionProtocol)

protocol = registry.get_protocol("MyDatabase.Protocol.MyProtocol")
assert isinstance(protocol, Protocol)

speaker_diarization = registry.get_protocol(
    "MyDatabase.SpeakerDiarization.MySpeakerDiarization"
)
assert isinstance(speaker_diarization, SpeakerDiarizationProtocol)

speaker_verification = registry.get_protocol(
    "MyDatabase.SpeakerVerification.MySpeakerVerification"
)
assert isinstance(speaker_verification, SpeakerVerificationProtocol)


files = list(collection.files())
assert len(files) == 2

files = list(protocol.files())
assert len(files) == 2

files = list(speaker_diarization.files())
assert len(files) == 2

files = list(speaker_verification.files())
assert len(files) == 2


meta_protocol = registry.get_protocol("X.SpeakerDiarization.MyMetaProtocol")
files = list(meta_protocol.train())
assert len(files) == 2

files = list(meta_protocol.development())
assert len(files) == 4
