// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EvidenceLedger {
    struct Record {
        bytes32 fileHash;
        uint256 timestamp;
        address submitter;
        bool exists;
    }

    mapping(string => Record) private records;
    event EvidenceStored(string caseId, bytes32 fileHash, uint256 timestamp);

    function storeEvidence(string calldata caseId, bytes32 fileHash) external {
        require(!records[caseId].exists, "Case already recorded");
        records[caseId] = Record(fileHash, block.timestamp, msg.sender, true);
        emit EvidenceStored(caseId, fileHash, block.timestamp);
    }

    function getEvidence(string calldata caseId)
        external
        view
        returns (bytes32, uint256, address)
    {
        require(records[caseId].exists, "No record");
        Record memory r = records[caseId];
        return (r.fileHash, r.timestamp, r.submitter);
    }
}

