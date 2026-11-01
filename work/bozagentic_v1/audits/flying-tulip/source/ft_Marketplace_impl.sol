// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.30;

import {IERC165, IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {
    OwnableUpgradeable
} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import {ReentrancyGuardTransient} from "@openzeppelin/contracts/utils/ReentrancyGuardTransient.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts/proxy/utils/UUPSUpgradeable.sol";
import {SafeCast} from "@openzeppelin/contracts/utils/math/SafeCast.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {EnumerableSet} from "@openzeppelin/contracts/utils/structs/EnumerableSet.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {
    EIP712Upgradeable
} from "@openzeppelin/contracts-upgradeable/utils/cryptography/EIP712Upgradeable.sol";
import {IftPUT} from "./interfaces/IftPUT.sol";
import {ISignatureTransfer} from "permit2/src/interfaces/ISignatureTransfer.sol";

/// @title Flying Tulip PUT Marketplace
/// @notice A marketplace for trading ERC721 pFT NFTs with Put validation
/// @dev Listings are invalidated if the underlying Put data changes (specifically ft or amountRemaining)
/// @dev Supports off-chain signed buy offers using Permit2 for token approvals for buy offers
/// @dev Supports Permit2 for direct ERC20 purchases in buy() function
contract pFTMarketplace is
    Initializable,
    OwnableUpgradeable,
    ReentrancyGuardTransient,
    UUPSUpgradeable,
    EIP712Upgradeable
{
    using EnumerableSet for EnumerableSet.AddressSet;
    using SafeERC20 for IERC20;

    event NewListing(
        uint256 indexed tokenId,
        address indexed seller,
        address token,
        uint256 price,
        uint256 expires
    );
    event EditListing(
        uint256 indexed tokenId,
        address indexed seller,
        address token,
        uint256 price,
        uint256 expires
    );
    event RemoveListing(uint256 indexed tokenId, address indexed seller);
    event Sold(
        uint256 indexed tokenId,
        address indexed seller,
        address buyer,
        uint256 price,
        uint256 makerFee,
        uint256 takerFee
    );

    event BuyOfferAccepted(
        address indexed buyer,
        address indexed seller,
        uint256 indexed tokenId,
        address token,
        uint256 price,
        uint256 makerFee,
        uint256 takerFee,
        bytes32 offerHash
    );
    event BuyOfferCancelled(address indexed buyer, uint256 nonce);

    event TokenAccepted(address indexed token);
    event TokenRemoved(address indexed token);
    event FeeRecipientUpdated(address recipient);
    event MakerFeeUpdated(uint16 fee);
    event TakerFeeUpdated(uint16 fee);
    event EmergencyPaused(bool paused);
    event FailedETHTransfer(address indexed to, uint256 amount);
    event GuardianSet(address indexed previous, address indexed current);

    error NotOwner();
    error NotApproved();
    error AlreadyListed();
    error NotListed();
    error PriceZero();
    error InsufficientPayment();
    error InvalidPutHash();
    error AlreadyExpired();
    error TransferFailed();
    error NotAcceptedToken();
    error NotExpectedToken();
    error NotExpectedPrice();
    error TokenAlreadyAdded();
    error InvalidTokenTransfer();
    error InvalidNativeValue();
    error InvalidNFT();
    error FeeRecipientZeroAddress();
    error FeeTooHigh();
    error ZeroAddress();
    error ListingTokenNotAllowed();
    error InvalidSignature();
    error OfferExpired();
    error NonceAlreadyUsed();
    error PutRequirementsNotMet();
    error InvalidBuyer();
    error ContractPaused();
    error InvalidTokenId();
    error DeadlineTooFar();
    error InvalidOfferParameters();
    error NoFailedTransfers();
    error InvalidPermit2Parameters();
    error UpgradeIncompatible(address newImplementation);
    error OnlyOwnerOrGuardian();

    struct Listing {
        // slot 0
        address seller; // cleared when deleting
        uint40 expires; // timestamp when listing expires (type(uint40).max = never)
        // slot 1
        address token; // address(0) means native
        uint96 price;
    }

    /// @notice Off-chain buy offer structure (not stored on-chain)
    struct BuyOffer {
        address buyer; // Address of the buyer
        address denominationToken; // Required token in the PUT
        uint96 minAmountRemaining; // Minimum amountRemaining required
        uint96 minFt; // Minimum FT amount required
        uint96 minStrike; // Minimum strike price required
        uint256 tokenId; // The tokenId the offer is for
        address paymentToken; // Token buyer will pay with (cannot be address(0))
        uint96 price; // Price buyer is willing to pay
        uint256 nonce; // Unique nonce for replay protection (separate from Permit2 nonce)
        uint40 deadline; // Deadline timestamp
    }

    /// @notice Parameters for Permit2 in buy function
    struct Permit2Details {
        uint256 nonce;
        uint40 deadline;
        bytes signature;
    }

    /// @notice Max fee rate allowed (10%)
    uint16 public constant MAX_FEE_RATE = 1000;

    /// @notice Max deadline allowed (180 days from now)
    uint256 public constant MAX_DEADLINE_DURATION = 180 days;

    /// @notice EIP-712 typehash for BuyOffer
    bytes32 public constant BUY_OFFER_TYPEHASH = keccak256(
        "BuyOffer(address buyer,address denominationToken,uint96 minAmountRemaining,uint96 minFt,uint96 minStrike,uint256 tokenId,address paymentToken,uint96 price,uint256 nonce,uint40 deadline)"
    );

    /// @notice The pFT NFT contract address
    IftPUT private _pFT;

    /// @notice Permit2 contract for token approvals
    ISignatureTransfer public permit2;

    /// @notice WETH token address (immutable, cannot be used as listing payment token)
    address public immutable WETH;

    // Fee settings
    /// @notice Maker fee rate in basis points (paid by seller)
    uint16 private _makerFeeRate;

    /// @notice Taker fee rate in basis points (paid by buyer)
    uint16 private _takerFeeRate;

    /// @notice Address where fees are sent
    address private _feeRecipient;

    /// @notice Emergency pause state
    bool private _paused;

    /// @notice Mapping to track failed ETH transfers for withdrawal
    mapping(address account => uint256 amount) public failedETHTransfers;

    mapping(uint256 tokenId => Listing listing) private _listings;

    /// @notice Track used nonces per buyer to prevent offer reuse
    mapping(address buyer => mapping(uint256 nonce => bool used)) public isNonceUsed;

    EnumerableSet.AddressSet private _acceptedTokens;

    /// @notice Address authorized to engage the emergency pause (cannot lift it).
    /// @dev Settable by the owner. Intended for a fast-path msig once ownership
    ///      is moved behind a Timelock. address(0) disables the role.
    address public guardian;

    modifier whenNotPaused() {
        _whenNotPaused();
        _;
    }

    function _whenNotPaused() internal view {
        if (_paused) revert ContractPaused();
    }

    // This modifier is only needed when this check is not done elsewhere.
    modifier validateTokenIdExists(uint256 tokenId) {
        _validateTokenIdExists(tokenId);
        _;
    }

    function _validateTokenIdExists(uint256 tokenId) internal view {
        // Check if tokenId exists by trying to get owner.
        try _pFT.ownerOf(tokenId) returns (address owner) {
            if (owner == address(0)) {
                revert InvalidTokenId();
            }
            // Token exists
        } catch {
            revert InvalidTokenId();
        }
    }

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor(address weth) {
        require(weth != address(0), ZeroAddress());
        WETH = weth;
        _disableInitializers();
    }

    /// @notice Initializes the contract (replaces constructor for proxy pattern)
    /// @param pFT The pFT NFT contract address
    /// @param initialFeeRecipient The address to receive marketplace fees
    /// @param initialMakerFeeRate The maker fee rate in basis points (paid by seller)
    /// @param initialTakerFeeRate The taker fee rate in basis points (paid by buyer)
    /// @param permit2Address The Permit2 contract address
    function initialize(
        IftPUT pFT,
        address initialFeeRecipient,
        uint16 initialMakerFeeRate,
        uint16 initialTakerFeeRate,
        address permit2Address
    )
        public
        initializer
    {
        __Ownable_init(msg.sender);
        __EIP712_init("pFTMarketplace", "1");

        // Confirm that it's an NFT
        if (!IERC165(pFT).supportsInterface(type(IERC721).interfaceId)) {
            revert InvalidNFT();
        }
        _pFT = pFT;

        // Set Permit2
        permit2 = ISignatureTransfer(permit2Address);

        // Set fee recipient and rate
        require(initialFeeRecipient != address(0), FeeRecipientZeroAddress());
        require(initialMakerFeeRate + initialTakerFeeRate <= MAX_FEE_RATE, FeeTooHigh());
        _feeRecipient = initialFeeRecipient;

        // Set maker/taker fees
        _setMakerTakerFees(initialMakerFeeRate, initialTakerFeeRate);

        // Add native token (address(0)) as an accepted payment method by default
        address[] memory defaultTokens = new address[](1);
        defaultTokens[0] = address(0);
        _addAcceptedTokens(defaultTokens);
    }

    /// @notice List an NFT for sale
    /// @param tokenId The token ID to list
    /// @param token The payment token address (address(0) for native)
    /// @param price The listing price in wei or token amount
    /// @param expires Timestamp when listing expires (use type(uint40).max for never)
    function addListing(
        uint256 tokenId,
        address token,
        uint256 price,
        uint40 expires
    )
        external
        whenNotPaused
    {
        require(price != 0, PriceZero());
        require(block.timestamp < expires, AlreadyExpired());
        require(_pFT.ownerOf(tokenId) == msg.sender, NotOwner());
        require(
            _pFT.getApproved(tokenId) == address(this)
                || _pFT.isApprovedForAll(msg.sender, address(this)),
            NotApproved()
        );
        require(
            _listings[tokenId].seller != msg.sender
                || _listings[tokenId].expires <= block.timestamp,
            AlreadyListed()
        );
        require(_acceptedTokens.contains(token), NotAcceptedToken());
        // For listings, WETH is not allowed as payment token
        require(token != WETH, ListingTokenNotAllowed());

        _listings[tokenId] = Listing({
            seller: msg.sender, token: token, price: SafeCast.toUint96(price), expires: expires
        });

        emit NewListing(tokenId, msg.sender, token, price, expires);
    }

    /// @notice Update the price and/or expiry of a listing
    /// @param tokenId The token ID
    /// @param token The new payment token address
    /// @param price The new price in wei or token amount
    /// @param expires The new expiry timestamp
    function editListing(
        uint256 tokenId,
        address token,
        uint256 price,
        uint256 expires
    )
        external
        whenNotPaused
        validateTokenIdExists(tokenId)
    {
        require(price != 0, PriceZero());
        require(block.timestamp < expires, AlreadyExpired());
        require(_acceptedTokens.contains(token), NotAcceptedToken());
        // For listings, WETH is not allowed as payment token
        require(token != WETH, ListingTokenNotAllowed());

        Listing storage listing = _listings[tokenId];
        require(listing.seller == msg.sender, NotOwner());

        listing.token = token;
        listing.price = SafeCast.toUint96(price);
        listing.expires = SafeCast.toUint40(expires);

        emit EditListing(tokenId, msg.sender, token, price, expires);
    }

    /// @notice Delist an NFT
    /// @param tokenId The token ID to delist
    function removeListing(uint256 tokenId) external {
        Listing memory listing = _listings[tokenId];

        require(listing.seller == msg.sender, NotOwner());

        _deleteListing(tokenId);

        emit RemoveListing(tokenId, msg.sender);
    }

    /// @notice Calculate combined fee for a given amount
    /// @param amount The amount to calculate fee for
    /// @return makerFee The calculated maker fee
    /// @return takerFee The calculated taker fee
    function calculateFees(uint256 amount)
        public
        view
        returns (uint256 makerFee, uint256 takerFee)
    {
        return (calculateMakerFee(amount), calculateTakerFee(amount));
    }

    /// @notice Calculate maker fee for a given amount (paid by seller)
    /// @param amount The amount to calculate maker fee for
    /// @return fee The calculated maker fee
    function calculateMakerFee(uint256 amount) public view returns (uint256) {
        return (amount * _makerFeeRate) / 10000;
    }

    /// @notice Calculate taker fee for a given amount (paid by buyer)
    /// @param amount The amount to calculate taker fee for
    /// @return fee The calculated taker fee
    function calculateTakerFee(uint256 amount) public view returns (uint256) {
        return (amount * _takerFeeRate) / 10000;
    }

    /// @notice Buy a listed NFT with either native or ERC20 tokens
    /// @param tokenId The token ID to buy
    /// @param expectedToken The expected payment token address (address(0) for native)
    /// @param expectedPrice The expected listing price to protect against price changes
    /// @param expectedPutHash The expected hash of the Put data to validate no changes occurred
    /// @param permit2Data Optional Permit2 signature data. If signature is empty, uses standard transferFrom
    function buy(
        uint256 tokenId,
        address expectedToken,
        uint256 expectedPrice,
        bytes32 expectedPutHash,
        Permit2Details calldata permit2Data
    )
        external
        payable
        nonReentrant
        whenNotPaused
    {
        Listing memory listing = _listings[tokenId];

        require(_listingExists(listing.seller), NotListed());
        require(block.timestamp < listing.expires, AlreadyExpired());
        require(listing.token == expectedToken, NotExpectedToken());
        require(listing.price == expectedPrice, NotExpectedPrice());
        require(_acceptedTokens.contains(listing.token), NotAcceptedToken());
        // Safety: enforce invariant that listing is never WETH
        require(listing.token != WETH, ListingTokenNotAllowed());

        // Validate that Put data hasn't changed BEFORE doing anything else
        bytes32 currentPutHash = getCurrentPutHash(tokenId);
        require(currentPutHash == expectedPutHash, InvalidPutHash());

        // Calculate fees
        uint256 makerFee = calculateMakerFee(listing.price);
        uint256 takerFee = calculateTakerFee(listing.price);
        uint256 totalFee = makerFee + takerFee;
        uint256 sellerAmount = listing.price - makerFee;
        uint256 buyerPaymentAmount = listing.price + takerFee;

        bool usePermit2 = permit2Data.signature.length > 0;

        if (listing.token == address(0)) {
            // Native payment
            require(msg.value >= buyerPaymentAmount, InsufficientPayment());
            require(!usePermit2, InvalidPermit2Parameters());
        } else {
            // ERC20 payment: no native value expected (cross function reentrancy guard)
            require(msg.value == 0, InvalidNativeValue());

            // Validate Permit2 parameters if using Permit2
            if (usePermit2) {
                require(
                    permit2Data.deadline <= block.timestamp + MAX_DEADLINE_DURATION,
                    DeadlineTooFar()
                );
                require(block.timestamp <= permit2Data.deadline, OfferExpired());
            }
        }

        // Effects: remove listing before any external calls to follow Checks-Effects-Interactions
        _deleteListing(tokenId);

        // Interaction: transfer NFT from seller to buyer first (if this reverts, no funds move)
        _pFT.safeTransferFrom(listing.seller, msg.sender, tokenId);

        // Interaction: distribute funds after NFT transfer
        if (listing.token == address(0)) {
            _distributeNativePayment(listing.seller, buyerPaymentAmount, sellerAmount, totalFee);
        } else {
            if (usePermit2) {
                _distributeERC20PaymentViaPermit2(
                    listing.token,
                    listing.seller,
                    buyerPaymentAmount,
                    sellerAmount,
                    totalFee,
                    permit2Data
                );
            } else {
                _distributeERC20PaymentViaTransferFrom(
                    listing.token, listing.seller, sellerAmount, totalFee
                );
            }
        }

        emit Sold(tokenId, listing.seller, msg.sender, listing.price, makerFee, takerFee);
    }

    /// @notice Distribute native ETH payment
    function _distributeNativePayment(
        address seller,
        uint256 buyerPaymentAmount,
        uint256 sellerAmount,
        uint256 totalFee
    )
        internal
    {
        address[] memory failedTos = new address[](3);
        uint256[] memory failedAmounts = new uint256[](3);
        uint256 failedCount = 0;

        // Send payment to seller
        uint256 failedAmount = _safeTransferETH(seller, sellerAmount);
        if (failedAmount != 0) {
            failedTos[failedCount] = seller;
            failedAmounts[failedCount] = failedAmount;
            ++failedCount;
        }

        // Send fees to fee recipient
        if (totalFee != 0) {
            address feeRecipient = _feeRecipient;
            failedAmount = _safeTransferETH(feeRecipient, totalFee);
            if (failedAmount != 0) {
                failedTos[failedCount] = feeRecipient;
                failedAmounts[failedCount] = failedAmount;
                ++failedCount;
            }
        }

        // Refund excess payment
        if (msg.value > buyerPaymentAmount) {
            failedAmount = _safeTransferETH(msg.sender, msg.value - buyerPaymentAmount);
            if (failedAmount != 0) {
                failedTos[failedCount] = msg.sender;
                failedAmounts[failedCount] = failedAmount;
                ++failedCount;
            }
        }

        // Update failed transfers (if any) after all sends are complete
        for (uint256 i = 0; i < failedCount; ++i) {
            failedETHTransfers[failedTos[i]] += failedAmounts[i];
        }
    }

    /// @notice Distribute ERC20 payment via Permit2
    function _distributeERC20PaymentViaPermit2(
        address token,
        address seller,
        uint256 totalPayment,
        uint256 sellerAmount,
        uint256 totalFee,
        Permit2Details calldata permit2Data
    )
        internal
    {
        // Use Permit2 to transfer total payment from buyer to this contract
        permit2.permitTransferFrom(
            ISignatureTransfer.PermitTransferFrom({
                permitted: ISignatureTransfer.TokenPermissions({
                    token: token, amount: totalPayment
                }),
                nonce: permit2Data.nonce,
                deadline: permit2Data.deadline
            }),
            ISignatureTransfer.SignatureTransferDetails({
                to: address(this), requestedAmount: totalPayment
            }),
            msg.sender,
            permit2Data.signature
        );

        // Distribute funds to seller
        IERC20(token).safeTransfer(seller, sellerAmount);

        // Distribute fees to fee recipient
        if (totalFee != 0) {
            IERC20(token).safeTransfer(_feeRecipient, totalFee);
        }
    }

    /// @notice Distribute ERC20 payment via safeTransferFrom
    function _distributeERC20PaymentViaTransferFrom(
        address token,
        address seller,
        uint256 sellerAmount,
        uint256 totalFee
    )
        internal
    {
        // Transfer tokens to seller
        IERC20(token).safeTransferFrom(msg.sender, seller, sellerAmount);

        // Transfer fee to fee recipient if != 0
        if (totalFee != 0) {
            IERC20(token).safeTransferFrom(msg.sender, _feeRecipient, totalFee);
        }
    }

    /// @notice Accept an off-chain signed buy offer using Permit2
    /// @param offer The buy offer details
    /// @param signature The buyer's signature of the offer
    /// @param permit2Signature The buyer's Permit2 signature for token transfer
    /// @param permit2Nonce The nonce for the Permit2 transfer (separate from offer hash)
    /// @param expectedPutHash The expected hash of the Put data to validate no changes occurred
    function acceptBuyOffer(
        BuyOffer calldata offer,
        bytes calldata signature,
        bytes calldata permit2Signature,
        uint256 permit2Nonce,
        bytes32 expectedPutHash
    )
        external
        nonReentrant
        whenNotPaused
    {
        // Validate offer and verify ownership/approval
        uint256 tokenId = offer.tokenId;
        bytes32 offerHash = _validateBuyOffer(offer, tokenId, signature, expectedPutHash);

        // Mark nonce as used to prevent reuse
        isNonceUsed[offer.buyer][offer.nonce] = true;

        _deleteListing(tokenId);

        // Transfer NFT from seller to buyer
        _pFT.safeTransferFrom(msg.sender, offer.buyer, tokenId);

        // Process payment via Permit2 and distribute funds
        (uint256 makerFee, uint256 takerFee) =
            _processOfferPayment(offer, permit2Signature, permit2Nonce);

        emit BuyOfferAccepted(
            offer.buyer,
            msg.sender,
            tokenId,
            offer.paymentToken,
            offer.price,
            makerFee,
            takerFee,
            offerHash
        );
    }

    /// @notice Cancel an off-chain buy offer by nonce
    /// @param nonce The nonce to cancel
    function cancelBuyOffer(uint256 nonce) external {
        require(!isNonceUsed[msg.sender][nonce], NonceAlreadyUsed());

        isNonceUsed[msg.sender][nonce] = true;

        emit BuyOfferCancelled(msg.sender, nonce);
    }

    /// @notice Withdraw failed ETH transfers
    function withdrawFailedTransfers() external {
        uint256 amount = failedETHTransfers[msg.sender];
        require(amount != 0, NoFailedTransfers());

        failedETHTransfers[msg.sender] = 0;

        // Send the full amount or revert state changes
        (bool success,) = msg.sender.call{value: amount}("");
        require(success, TransferFailed());
    }

    /// @notice Safe ETH transfer with fallback to failed transfers mapping
    /// @param to The recipient address
    /// @param amount The amount to transfer
    function _safeTransferETH(address to, uint256 amount) internal returns (uint256 sent) {
        if (amount != 0) {
            (bool success,) = to.call{value: amount}("");
            if (!success) {
                // If transfer fails, will be added to failed transfers for later withdrawal
                emit FailedETHTransfer(to, amount);
                return amount;
            }
        }
        return 0;
    }

    /// @notice Check if an NFT meets buy offer requirements
    /// @param offer The buy offer
    /// @param tokenId The token ID to check
    /// @return bool True if the NFT meets the offer requirements
    function doesTokenMeetOfferRequirements(
        BuyOffer calldata offer,
        uint256 tokenId
    )
        external
        view
        returns (bool)
    {
        try _pFT.puts(tokenId) returns (IftPUT.Put memory put) {
            return put.token == offer.denominationToken
                && put.amountRemaining >= offer.minAmountRemaining && put.ft >= offer.minFt
                && put.strike >= offer.minStrike;
        } catch {
            return false;
        }
    }

    /// @notice Verify a buy offer signature
    /// @param offer The buy offer
    /// @param signature The signature to verify
    /// @return signer The address that signed the offer
    function verifyBuyOfferSignature(
        BuyOffer calldata offer,
        bytes calldata signature
    )
        external
        view
        returns (address)
    {
        return _verifyBuyOfferSignature(offer, signature);
    }

    /// @notice Get the hash of a buy offer
    /// @param offer The buy offer
    /// @return The hash of the offer
    function getBuyOfferHash(BuyOffer calldata offer) external view returns (bytes32) {
        return _hashBuyOffer(offer);
    }

    function _hashBuyOffer(BuyOffer calldata offer) internal view returns (bytes32) {
        return _hashTypedDataV4(
            keccak256(
                abi.encode(
                    BUY_OFFER_TYPEHASH,
                    offer.buyer,
                    offer.denominationToken,
                    offer.minAmountRemaining,
                    offer.minFt,
                    offer.minStrike,
                    offer.tokenId,
                    offer.paymentToken,
                    offer.price,
                    offer.nonce,
                    offer.deadline
                )
            )
        );
    }

    function _verifyBuyOfferSignature(
        BuyOffer calldata offer,
        bytes calldata signature
    )
        internal
        view
        returns (address)
    {
        bytes32 hash = _hashBuyOffer(offer);
        (address signer, ECDSA.RecoverError err,) = ECDSA.tryRecover(hash, signature);
        if (err != ECDSA.RecoverError.NoError) {
            return address(0);
        }
        return signer;
    }

    /// @notice Validate a buy offer's parameters, signature, ownership, and PUT requirements
    /// @param offer The buy offer to validate
    /// @param tokenId The token ID being sold
    /// @param signature The buyer's signature
    /// @param expectedPutHash The expected PUT hash
    /// @return offerHash The hash of the validated offer
    function _validateBuyOffer(
        BuyOffer calldata offer,
        uint256 tokenId,
        bytes calldata signature,
        bytes32 expectedPutHash
    )
        internal
        view
        returns (bytes32 offerHash)
    {
        // Validate offer parameters
        require(offer.price != 0, InvalidOfferParameters());
        require(offer.buyer != address(0), InvalidBuyer());
        require(offer.deadline <= block.timestamp + MAX_DEADLINE_DURATION, DeadlineTooFar());

        // Verify offer hasn't expired
        require(block.timestamp <= offer.deadline, OfferExpired());

        // Verify nonce hasn't been used
        require(!isNonceUsed[offer.buyer][offer.nonce], NonceAlreadyUsed());

        // Verify signature
        offerHash = _hashBuyOffer(offer);
        address signer = _verifyBuyOfferSignature(offer, signature);
        require(signer == offer.buyer, InvalidSignature());

        // Verify seller owns the NFT and has approved marketplace
        require(_pFT.ownerOf(tokenId) == msg.sender, NotOwner());
        require(
            _pFT.getApproved(tokenId) == address(this)
                || _pFT.isApprovedForAll(msg.sender, address(this)),
            NotApproved()
        );

        // Verify PUT meets requirements
        IftPUT.Put memory put = _pFT.puts(tokenId);
        require(put.token == offer.denominationToken, PutRequirementsNotMet());
        require(put.amountRemaining >= offer.minAmountRemaining, PutRequirementsNotMet());
        require(put.ft >= offer.minFt, PutRequirementsNotMet());
        require(put.strike >= offer.minStrike, PutRequirementsNotMet());

        // Validate that Put data hasn't changed since offer was made
        bytes32 currentPutHash = getCurrentPutHash(tokenId);
        require(currentPutHash == expectedPutHash, InvalidPutHash());

        // Verify payment token is accepted
        require(_acceptedTokens.contains(offer.paymentToken), NotAcceptedToken());
        // For offers, native ETH is not allowed
        require(offer.paymentToken != address(0), InvalidNativeValue());
    }

    /// @notice Process payment for a buy offer via Permit2
    /// @param offer The buy offer details
    /// @param permit2Signature The buyer's Permit2 signature
    /// @param permit2Nonce The nonce for the Permit2 transfer
    /// @return makerFee The maker fee amount
    /// @return takerFee The taker fee amount
    function _processOfferPayment(
        BuyOffer calldata offer,
        bytes calldata permit2Signature,
        uint256 permit2Nonce
    )
        internal
        returns (uint256 makerFee, uint256 takerFee)
    {
        makerFee = calculateMakerFee(offer.price);
        takerFee = calculateTakerFee(offer.price);
        uint256 totalPayment = offer.price + takerFee;
        uint256 sellerAmount = offer.price - makerFee;
        uint256 totalFee = makerFee + takerFee;

        // Use Permit2 to transfer total payment from buyer to this contract
        permit2.permitTransferFrom(
            ISignatureTransfer.PermitTransferFrom({
                permitted: ISignatureTransfer.TokenPermissions({
                    token: offer.paymentToken, amount: totalPayment
                }),
                nonce: permit2Nonce,
                deadline: offer.deadline
            }),
            ISignatureTransfer.SignatureTransferDetails({
                to: address(this), requestedAmount: totalPayment
            }),
            offer.buyer,
            permit2Signature
        );

        // Distribute funds to seller
        IERC20(offer.paymentToken).safeTransfer(msg.sender, sellerAmount);

        // Distribute fees to fee recipient
        if (totalFee != 0) {
            IERC20(offer.paymentToken).safeTransfer(_feeRecipient, totalFee);
        }
    }

    /// @notice Check if a listing is still valid
    /// @param owner The expected owner address
    /// @param tokenId The token ID
    /// @return bool True if listing exists, owner matches, and approval is set
    function isListingValid(address owner, uint256 tokenId) external view returns (bool) {
        Listing memory listing = _listings[tokenId];
        bool isLister = listing.seller == owner;
        if (!isLister) {
            return false;
        }

        bool hasExpired = listing.expires <= block.timestamp;
        if (hasExpired) {
            return false;
        }

        try _pFT.ownerOf(tokenId) returns (address currentOwner) {
            if (currentOwner != owner) {
                return false;
            }
        } catch {
            return false;
        }

        bool hasApproval = _pFT.getApproved(tokenId) == address(this)
            || _pFT.isApprovedForAll(owner, address(this));
        if (!hasApproval) {
            return false;
        }

        return true;
    }

    /// @notice Get listing details
    /// @param tokenId The token ID
    /// @return listing The listing details
    function getListing(uint256 tokenId) external view returns (Listing memory) {
        return _listings[tokenId];
    }

    /// @notice Get Put hash from individual parameters
    /// @param tokenId The token ID
    /// @param token The token address
    /// @param amountRemaining The amount of denomination asset available
    /// @param ft The current FT amount available
    /// @return The keccak256 hash of the Put parameters
    function getPutHash(
        uint256 tokenId,
        address token,
        uint96 amountRemaining,
        uint96 ft
    )
        public
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(tokenId, token, amountRemaining, ft));
    }

    /// @notice Get the current Put hash for a token
    /// @param tokenId The token ID
    /// @return putHash The current hash of the Put data
    function getCurrentPutHash(uint256 tokenId) public view returns (bytes32 putHash) {
        IftPUT.Put memory put = IftPUT(_pFT).puts(tokenId);
        return getPutHash(tokenId, put.token, put.amountRemaining, put.ft);
    }

    /// @notice Check if a token is accepted for payment
    /// @param token The token address
    /// @return bool True if the token is accepted for payment
    function isTokenAccepted(address token) external view returns (bool) {
        return _acceptedTokens.contains(token);
    }

    /// @notice Get the list of accepted payment tokens
    /// @return tokens The array of accepted token addresses
    function getAcceptedTokens() external view returns (address[] memory) {
        uint256 length = _acceptedTokens.length();
        address[] memory tokens = new address[](length);
        for (uint256 i = 0; i < length; ++i) {
            tokens[i] = _acceptedTokens.at(i);
        }
        return tokens;
    }

    /// @notice Get the current maker fee rate (paid by seller)
    /// @return The current maker fee rate in basis points
    function getMakerFeeRate() external view returns (uint16) {
        return _makerFeeRate;
    }

    /// @notice Get the current taker fee rate (paid by buyer)
    /// @return The current taker fee rate in basis points
    function getTakerFeeRate() external view returns (uint16) {
        return _takerFeeRate;
    }

    /// @notice Get the fee recipient address
    /// @return The address receiving marketplace fees
    function getFeeRecipient() external view returns (address) {
        return _feeRecipient;
    }

    /// @notice Check if the contract is paused
    /// @return bool True if the contract is paused
    function isPaused() external view returns (bool) {
        return _paused;
    }

    // Only removes seller for gas efficiency
    function _deleteListing(uint256 tokenId) private {
        delete _listings[tokenId].seller;
    }

    function _listingExists(address seller) private pure returns (bool) {
        return seller != address(0);
    }

    function _addAcceptedTokens(address[] memory tokens) private {
        for (uint256 i = 0; i < tokens.length; ++i) {
            bool added = _acceptedTokens.add(tokens[i]);
            require(added, TokenAlreadyAdded());
            emit TokenAccepted(tokens[i]);
        }
    }

    /// @notice Toggle the emergency pause.
    /// @dev Pausing (paused == true) is callable by owner or guardian.
    ///      Unpausing (paused == false) is owner-only — a compromised guardian
    ///      cannot lift a pause that the owner engaged.
    /// @param paused The new pause state.
    function setEmergencyPause(bool paused) external {
        if (paused) {
            if (msg.sender != owner() && msg.sender != guardian) revert OnlyOwnerOrGuardian();
        } else {
            _checkOwner();
        }
        _paused = paused;
        emit EmergencyPaused(paused);
    }

    /// @notice Set or rotate the guardian. Owner only. Pass address(0) to disable.
    /// @param newGuardian The new guardian address (or address(0) to clear).
    function setGuardian(address newGuardian) external onlyOwner {
        address prev = guardian;
        guardian = newGuardian;
        emit GuardianSet(prev, newGuardian);
    }

    /// @notice Update the maker/taker fee distribution
    /// @param makerFeeRate The new maker fee rate in basis points
    /// @param takerFeeRate The new taker fee rate in basis points
    function setMakerTakerFees(uint16 makerFeeRate, uint16 takerFeeRate) external onlyOwner {
        _setMakerTakerFees(makerFeeRate, takerFeeRate);
    }

    function _setMakerTakerFees(uint16 makerFeeRate, uint16 takerFeeRate) internal {
        uint16 newTotalFee = makerFeeRate + takerFeeRate;
        require(newTotalFee <= MAX_FEE_RATE, FeeTooHigh());

        _makerFeeRate = makerFeeRate;
        _takerFeeRate = takerFeeRate;

        emit MakerFeeUpdated(makerFeeRate);
        emit TakerFeeUpdated(takerFeeRate);
    }

    /// @notice Update the fee recipient address
    /// @param newFeeRecipient The new address to receive fees
    function setFeeRecipient(address newFeeRecipient) external onlyOwner {
        require(newFeeRecipient != address(0), FeeRecipientZeroAddress());
        _feeRecipient = newFeeRecipient;
        emit FeeRecipientUpdated(newFeeRecipient);
    }

    /// @notice Add accepted payment tokens
    /// @param tokens The array of token addresses to accept
    function addAcceptedTokens(address[] memory tokens) external onlyOwner {
        _addAcceptedTokens(tokens);
    }

    /// @notice Remove accepted payment tokens
    /// @param tokens The array of token addresses to remove
    function removeAcceptedTokens(address[] calldata tokens) external onlyOwner {
        for (uint256 i = 0; i < tokens.length; ++i) {
            if (_acceptedTokens.remove(tokens[i])) {
                emit TokenRemoved(tokens[i]);
            }
        }
    }

    /// @notice Authorize an upgrade to the implementation contract
    /// @dev Only the contract owner can authorize upgrades
    /// @param newImplementation The address of the new implementation
    function _authorizeUpgrade(address newImplementation) internal view override onlyOwner {
        // Prevent upgrades that change WETH wiring
        if (pFTMarketplace(newImplementation).WETH() != address(WETH)) {
            revert UpgradeIncompatible(newImplementation);
        }
    }
}
